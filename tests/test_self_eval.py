"""Tests for src/costdna/self_eval.py — accuracy-drift monitoring."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from costdna.self_eval import (_wilson_ci, run_self_eval)


def test_wilson_ci_basic():
    """Sanity: 5/10 should be wide; 50/100 narrow; both centered near 0.5."""
    lo_small, hi_small = _wilson_ci(5, 10)
    lo_large, hi_large = _wilson_ci(50, 100)
    assert 0.0 < lo_small < 0.5 < hi_small < 1.0
    assert 0.0 < lo_large < 0.5 < hi_large < 1.0
    assert (hi_small - lo_small) > (hi_large - lo_large)


def test_wilson_ci_edge_cases():
    """0/n and n/n shouldn't return NaN; should give honest one-sided bounds."""
    lo, hi = _wilson_ci(0, 10)
    assert lo == 0.0
    assert 0.0 < hi < 0.5
    lo, hi = _wilson_ci(10, 10)
    assert hi == 1.0
    assert 0.5 < lo < 1.0
    # Degenerate input — return (0,0) rather than dividing by zero.
    assert _wilson_ci(0, 0) == (0.0, 0.0)


def _write_predictions(dir_: Path, rows: list[dict]):
    dir_.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(dir_ / "predictions.csv", index=False)


def test_perfect_match_returns_100_percent(tmp_path):
    """Both runs predict every label correctly → 100% overall, delta 0."""
    labels = pd.DataFrame([
        {"resource_id": "r1", "team": "backend"},
        {"resource_id": "r2", "team": "data"},
        {"resource_id": "r3", "team": "ml"},
    ])
    labels_path = tmp_path / "labels.csv"
    labels.to_csv(labels_path, index=False)

    base = tmp_path / "runs" / "2026-01-01"
    curr = tmp_path / "runs" / "2026-02-01"
    _write_predictions(base, [
        {"resource_id": "r1", "team_pred": "backend", "confidence": 0.95},
        {"resource_id": "r2", "team_pred": "data", "confidence": 0.93},
        {"resource_id": "r3", "team_pred": "ml", "confidence": 0.91},
    ])
    _write_predictions(curr, [
        {"resource_id": "r1", "team_pred": "backend", "confidence": 0.96},
        {"resource_id": "r2", "team_pred": "data", "confidence": 0.94},
        {"resource_id": "r3", "team_pred": "ml", "confidence": 0.90},
    ])

    rep = run_self_eval(base, curr, labels_path)
    assert rep.n_labels == 3
    assert rep.baseline_overall.accuracy == 1.0
    assert rep.current_overall.accuracy == 1.0
    assert rep.overall_delta == 0.0
    assert rep.significant_change is False


def test_real_degradation_is_flagged(tmp_path):
    """A 100% → 50% drop on 20 labels should flag as significant."""
    rids = [f"r{i}" for i in range(20)]
    labels = pd.DataFrame({"resource_id": rids, "team": ["backend"] * 20})
    labels_path = tmp_path / "labels.csv"
    labels.to_csv(labels_path, index=False)

    base = tmp_path / "runs" / "baseline"
    curr = tmp_path / "runs" / "current"
    _write_predictions(base, [
        {"resource_id": r, "team_pred": "backend", "confidence": 0.9}
        for r in rids
    ])
    _write_predictions(curr, [
        # Half right, half wrong.
        {"resource_id": r, "team_pred": "backend" if i < 10 else "ml",
         "confidence": 0.7}
        for i, r in enumerate(rids)
    ])

    rep = run_self_eval(base, curr, labels_path)
    assert rep.baseline_overall.accuracy == 1.0
    assert rep.current_overall.accuracy == 0.5
    assert rep.overall_delta == -0.5
    assert rep.significant_change is True


def test_small_random_noise_is_not_flagged(tmp_path):
    """1/15 → 2/15 (a single coin-flip kind of change) should NOT flag as
    significant — confidence intervals overlap heavily on tiny samples."""
    rids = [f"r{i}" for i in range(15)]
    labels = pd.DataFrame({"resource_id": rids, "team": ["backend"] * 15})
    labels_path = tmp_path / "labels.csv"
    labels.to_csv(labels_path, index=False)

    base = tmp_path / "runs" / "baseline"
    curr = tmp_path / "runs" / "current"
    _write_predictions(base, [
        {"resource_id": r,
         "team_pred": "backend" if i != 0 else "data",
         "confidence": 0.85}
        for i, r in enumerate(rids)
    ])
    _write_predictions(curr, [
        {"resource_id": r,
         "team_pred": "backend" if i > 1 else "data",
         "confidence": 0.84}
        for i, r in enumerate(rids)
    ])

    rep = run_self_eval(base, curr, labels_path)
    # 14/15 → 13/15, that's about a 6 point drop on a noisy sample.
    assert rep.significant_change is False, (
        "single-resource changes on 15 labels should not be flagged as significant"
    )


def test_legacy_team_column_renamed_to_team_pred(tmp_path):
    """Older predictions.csv files use 'team' instead of 'team_pred' — the
    self-eval module should silently rename to keep backward compat."""
    rids = ["r1", "r2", "r3"]
    labels = pd.DataFrame({"resource_id": rids, "team": ["backend"] * 3})
    labels_path = tmp_path / "labels.csv"
    labels.to_csv(labels_path, index=False)

    base = tmp_path / "runs" / "baseline"
    curr = tmp_path / "runs" / "current"
    # Use 'team' instead of 'team_pred' to simulate older format.
    _write_predictions(base, [
        {"resource_id": "r1", "team": "backend", "confidence": 0.9},
        {"resource_id": "r2", "team": "backend", "confidence": 0.9},
        {"resource_id": "r3", "team": "backend", "confidence": 0.9},
    ])
    _write_predictions(curr, [
        {"resource_id": "r1", "team": "backend", "confidence": 0.9},
        {"resource_id": "r2", "team": "backend", "confidence": 0.9},
        {"resource_id": "r3", "team": "backend", "confidence": 0.9},
    ])

    rep = run_self_eval(base, curr, labels_path)
    assert rep.baseline_overall.accuracy == 1.0


def test_as_markdown_renders_without_crash(tmp_path):
    """The markdown serializer should produce a non-empty string with the
    expected sections so the Slack/Discord integration can rely on it."""
    rids = [f"r{i}" for i in range(10)]
    labels = pd.DataFrame({
        "resource_id": rids,
        "team": ["backend"] * 5 + ["ml"] * 5,
    })
    labels_path = tmp_path / "labels.csv"
    labels.to_csv(labels_path, index=False)

    base = tmp_path / "runs" / "baseline"
    curr = tmp_path / "runs" / "current"
    _write_predictions(base, [
        {"resource_id": r, "team_pred": "backend" if i < 5 else "ml",
         "confidence": 0.9} for i, r in enumerate(rids)
    ])
    _write_predictions(curr, [
        # 1 wrong prediction in each team.
        {"resource_id": r,
         "team_pred": "ml" if i == 0 else ("backend" if i < 5 else "ml"),
         "confidence": 0.85}
        for i, r in enumerate(rids)
    ])

    rep = run_self_eval(base, curr, labels_path)
    md = rep.as_markdown()
    assert "## " in md and "CostDNA self-eval" in md
    assert "Overall accuracy" in md
    assert "| `backend` |" in md
    assert "| `ml` |" in md
