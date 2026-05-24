"""Self-monitoring: track prediction accuracy on a labeled subset over time.

Drift detection (``costdna.drift``) catches changes in what the model
predicts. Self-eval catches changes in *whether the predictions are
correct*. The two complement each other — production ML systems need both.

The minimum-viable version (this module): given two scan output directories
and a ground-truth labels file, compute per-team accuracy on both runs and
report the delta with a Wilson 95% confidence interval. That's enough to
distinguish "real degradation" from "test-set noise" without standing up a
full evaluation harness.

Full version (issue #4): adds Slack/Discord webhook integration to surface
the delta in the daily digest. This module ships the math; the webhook
wiring is a small additional step on top.

Schema expected:

  predictions.csv  — columns: resource_id, team_pred, confidence
  labels.csv       — columns: resource_id, team (ground truth)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

__all__ = ["SelfEvalReport", "PerTeamAccuracy", "run_self_eval"]


@dataclass
class PerTeamAccuracy:
    team: str
    n_labeled: int
    n_correct: int
    accuracy: float
    ci_low: float        # Wilson 95% lower bound
    ci_high: float       # Wilson 95% upper bound


@dataclass
class SelfEvalReport:
    baseline_run: str
    current_run: str
    n_labels: int
    baseline_overall: PerTeamAccuracy
    current_overall: PerTeamAccuracy
    per_team_baseline: list[PerTeamAccuracy] = field(default_factory=list)
    per_team_current: list[PerTeamAccuracy] = field(default_factory=list)
    overall_delta: float = 0.0
    significant_change: bool = False    # CI of delta doesn't include 0

    def as_markdown(self) -> str:
        """Render a Slack/Discord-friendly markdown summary."""
        sign = "+" if self.overall_delta >= 0 else ""
        marker = "⚠️ " if self.significant_change else ""
        lines = [
            f"## {marker}CostDNA self-eval: {self.baseline_run} → {self.current_run}",
            "",
            f"**Overall accuracy: {self.baseline_overall.accuracy:.1%} → "
            f"{self.current_overall.accuracy:.1%} "
            f"({sign}{self.overall_delta:+.1%})**",
            "",
            f"Labels: {self.n_labels}. CIs are Wilson 95%.",
            "",
            "| Team | Baseline | Current | Δ |",
            "|---|---|---|---|",
        ]
        # join per-team rows
        baseline_by_team = {t.team: t for t in self.per_team_baseline}
        for cur in self.per_team_current:
            base = baseline_by_team.get(cur.team)
            if base is None:
                continue
            delta = cur.accuracy - base.accuracy
            lines.append(
                f"| `{cur.team}` "
                f"| {base.accuracy:.1%} ({base.n_correct}/{base.n_labeled}) "
                f"| {cur.accuracy:.1%} ({cur.n_correct}/{cur.n_labeled}) "
                f"| {delta:+.1%} |"
            )
        return "\n".join(lines)


def _wilson_ci(n_correct: int, n_total: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for a binomial proportion.

    More appropriate than the normal approximation for the small-sample
    regimes self-eval typically runs on (10-100 labels). Returns (low, high).
    """
    if n_total == 0:
        return (0.0, 0.0)
    p = n_correct / n_total
    denom = 1.0 + z * z / n_total
    center = (p + z * z / (2 * n_total)) / denom
    margin = (z * math.sqrt(p * (1 - p) / n_total + z * z / (4 * n_total**2))) / denom
    return (max(0.0, center - margin), min(1.0, center + margin))


def _accuracy_for(
    preds: pd.DataFrame, labels: pd.DataFrame, team: str | None = None
) -> PerTeamAccuracy:
    # Rename the labels' team column to team_true up-front so the merge
    # produces a stable column name regardless of overlap with preds.
    labels_renamed = labels.rename(columns={"team": "team_true"})
    merged = preds.merge(labels_renamed, on="resource_id")
    if team is not None:
        merged = merged[merged["team_true"] == team]
    if len(merged) == 0:
        return PerTeamAccuracy(
            team=team or "_all", n_labeled=0, n_correct=0,
            accuracy=0.0, ci_low=0.0, ci_high=0.0,
        )
    correct = int((merged["team_pred"] == merged["team_true"]).sum())
    total = int(len(merged))
    lo, hi = _wilson_ci(correct, total)
    return PerTeamAccuracy(
        team=team or "_all", n_labeled=total, n_correct=correct,
        accuracy=correct / total, ci_low=lo, ci_high=hi,
    )


def run_self_eval(
    baseline_dir: Path | str,
    current_dir: Path | str,
    labels_path: Path | str,
) -> SelfEvalReport:
    """Compare predictions in two scan directories against ground-truth labels.

    Parameters
    ----------
    baseline_dir : path
        Directory containing ``predictions.csv`` from an earlier scan.
    current_dir : path
        Directory containing ``predictions.csv`` from the latest scan.
    labels_path : path
        CSV with ground-truth labels (``resource_id``, ``team``). Assumed
        stable across the two runs — a label that changed ownership in the
        period covered by the two scans is a real edit and would skew the
        accuracy delta. This is by design: self-eval measures the model,
        not the labeling.

    Returns
    -------
    SelfEvalReport
        Aggregate + per-team accuracy on both runs, with Wilson 95% CIs
        and a ``significant_change`` flag (overall delta CI excludes 0).
    """
    baseline_dir = Path(baseline_dir)
    current_dir = Path(current_dir)
    labels_path = Path(labels_path)

    base_preds = pd.read_csv(baseline_dir / "predictions.csv")
    curr_preds = pd.read_csv(current_dir / "predictions.csv")
    labels = pd.read_csv(labels_path)

    if "team_pred" not in base_preds.columns and "team" in base_preds.columns:
        base_preds = base_preds.rename(columns={"team": "team_pred"})
    if "team_pred" not in curr_preds.columns and "team" in curr_preds.columns:
        curr_preds = curr_preds.rename(columns={"team": "team_pred"})

    teams = sorted(set(labels["team"]))
    per_team_b = [_accuracy_for(base_preds, labels, t) for t in teams]
    per_team_c = [_accuracy_for(curr_preds, labels, t) for t in teams]
    overall_b = _accuracy_for(base_preds, labels)
    overall_c = _accuracy_for(curr_preds, labels)

    delta = overall_c.accuracy - overall_b.accuracy
    # A 95% CI on the delta of two independent proportions is approximately
    # delta ± 1.96 * sqrt(var_b + var_c). We use this as a quick "is the
    # change real?" check rather than a formal test of significance.
    var_b = overall_b.accuracy * (1 - overall_b.accuracy) / max(1, overall_b.n_labeled)
    var_c = overall_c.accuracy * (1 - overall_c.accuracy) / max(1, overall_c.n_labeled)
    margin = 1.96 * math.sqrt(var_b + var_c)
    significant = abs(delta) > margin

    return SelfEvalReport(
        baseline_run=baseline_dir.name,
        current_run=current_dir.name,
        n_labels=int(len(labels)),
        baseline_overall=overall_b,
        current_overall=overall_c,
        per_team_baseline=per_team_b,
        per_team_current=per_team_c,
        overall_delta=delta,
        significant_change=significant,
    )
