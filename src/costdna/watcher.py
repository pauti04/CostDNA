"""Continuous scanning + drift digest.

`costdna watch` runs on cron (or as a daemon) and:

  1. Performs a full scan, saving predictions to a date-stamped directory
  2. Diffs against the most recent prior scan
  3. Computes a digest:
        - new resources since last scan
        - resources that changed predicted team (drift)
        - newly low-confidence resources (model lost confidence over time)
        - new anomalies (resources flagged that weren't before)
  4. Posts the digest to Slack / Discord webhook (or just stdout)

This is what makes CostDNA usable as ongoing infra rather than a one-shot
tool. FinOps teams configure it once, get weekly digests in #cloud-cost,
catch drift before the bill blows up.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)


@dataclass
class Digest:
    timestamp: str
    new_resources: int
    drifted_resources: list[dict]            # team change events
    newly_low_confidence: list[dict]
    new_anomalies: list[dict]
    total_resources: int
    by_team_dollars: dict[str, float]
    prev_run_dir: str | None
    this_run_dir: str

    def to_markdown(self) -> str:
        """Render as a Slack-flavored markdown blob."""
        ts = self.timestamp.split("T")[0]
        lines = [f"*CostDNA digest — {ts}*"]
        lines.append(f"_{self.total_resources} resources scanned_")
        lines.append("")

        if self.new_resources:
            lines.append(f"🆕 *{self.new_resources} new resources* since last run")
        if self.drifted_resources:
            lines.append(f"⚠ *{len(self.drifted_resources)} resources changed team*")
            for ev in self.drifted_resources[:5]:
                lines.append(f"   • `{ev['resource_id']}`: "
                             f"{ev['old_team']} → *{ev['new_team']}* "
                             f"(conf {ev['old_confidence']:.2f} → {ev['new_confidence']:.2f}) "
                             f"_{ev['severity']}_")
            if len(self.drifted_resources) > 5:
                lines.append(f"   _… and {len(self.drifted_resources) - 5} more_")
        if self.newly_low_confidence:
            lines.append(f"🤔 *{len(self.newly_low_confidence)} resources lost confidence*")
        if self.new_anomalies:
            lines.append(f"🚨 *{len(self.new_anomalies)} new anomalies* "
                         "(don't fit any team — investigate)")
            for a in self.new_anomalies[:5]:
                lines.append(f"   • `{a['resource_id']}`: "
                             f"conf {a['confidence']:.2f}, "
                             f"{a['z_score']:+.1f}σ from {a['predicted_team']}")

        if not (self.new_resources or self.drifted_resources or
                self.newly_low_confidence or self.new_anomalies):
            lines.append("✅ No changes since last run.")

        if self.by_team_dollars:
            lines.append("")
            lines.append("*Spend by team*")
            for team, dollars in sorted(self.by_team_dollars.items(),
                                         key=lambda kv: -kv[1])[:6]:
                lines.append(f"   • {team}: ${dollars:,.2f}")

        return "\n".join(lines)


def _previous_run_dir(state_dir: Path, before: str) -> Path | None:
    """Most recent run dir under state_dir whose name (a date) sorts before `before`."""
    if not state_dir.exists():
        return None
    candidates = sorted(
        [d for d in state_dir.iterdir() if d.is_dir() and d.name < before],
        reverse=True,
    )
    return candidates[0] if candidates else None


def _load_predictions(run_dir: Path) -> pd.DataFrame | None:
    p = run_dir / "predictions.csv"
    if not p.exists():
        return None
    return pd.read_csv(p)


def _load_anomalies(run_dir: Path) -> list[dict]:
    p = run_dir / "anomalies.json"
    if not p.exists():
        return []
    return json.loads(p.read_text())


def build_digest(this_run_dir: Path, state_dir: Path,
                 confidence_threshold: float = 0.7) -> Digest:
    """Compare a freshly-completed scan against the previous run in state_dir."""
    cur = _load_predictions(this_run_dir)
    if cur is None:
        raise FileNotFoundError(f"{this_run_dir}/predictions.csv missing")

    prev_dir = _previous_run_dir(state_dir, this_run_dir.name)
    prev = _load_predictions(prev_dir) if prev_dir else None

    drifted: list[dict] = []
    newly_low_conf: list[dict] = []
    new_count = 0
    if prev is not None:
        prev_ids = set(prev["resource_id"])
        cur_ids = set(cur["resource_id"])
        new_count = len(cur_ids - prev_ids)

        from costdna.drift import compute_drift
        events = compute_drift(prev, cur, confidence_threshold=confidence_threshold)
        for e in events:
            drifted.append({
                "resource_id": e.resource_id,
                "old_team": e.old_team,
                "new_team": e.new_team,
                "old_confidence": e.old_confidence,
                "new_confidence": e.new_confidence,
                "severity": e.severity,
            })

        # "Lost confidence": same team, but moved across the threshold downward.
        merged = prev.merge(cur, on="resource_id", suffixes=("_old", "_new"))
        same_team = merged[merged["team_pred_old"] == merged["team_pred_new"]]
        lost = same_team[(same_team["confidence_old"] >= confidence_threshold)
                         & (same_team["confidence_new"] < confidence_threshold)]
        newly_low_conf = lost[["resource_id", "team_pred_new",
                                "confidence_old", "confidence_new"]].to_dict("records")

    # New anomalies = anomalies in this run that weren't in the previous one.
    cur_anom = _load_anomalies(this_run_dir)
    prev_anom_ids = {a["resource_id"] for a in
                     (_load_anomalies(prev_dir) if prev_dir else [])}
    new_anom = [a for a in cur_anom if a["resource_id"] not in prev_anom_ids]

    # Spend rollup.
    by_team: dict[str, float] = {}
    if "confidence" in cur.columns and "team_pred" in cur.columns:
        # If predictions.csv has a 'cost' column we use it; otherwise just count.
        if "cost" in cur.columns:
            by_team = cur.groupby("team_pred")["cost"].sum().to_dict()

    return Digest(
        timestamp=datetime.now(timezone.utc).isoformat(),
        new_resources=new_count,
        drifted_resources=drifted,
        newly_low_confidence=newly_low_conf,
        new_anomalies=new_anom,
        total_resources=len(cur),
        by_team_dollars=by_team,
        prev_run_dir=str(prev_dir) if prev_dir else None,
        this_run_dir=str(this_run_dir),
    )


def post_to_slack(digest: Digest, webhook_url: str) -> bool:
    """Slack and Discord both accept this same `text=` payload format."""
    body = json.dumps({"text": digest.to_markdown()}).encode()
    req = urllib.request.Request(
        webhook_url, data=body, method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return 200 <= resp.status < 300
    except urllib.error.HTTPError as e:
        log.warning("webhook %s returned %d: %s", webhook_url, e.code, e.reason)
        return False
    except Exception as e:
        log.warning("webhook post failed: %s", e)
        return False


def write_digest(digest: Digest, out_dir: Path) -> Path:
    """Save the digest as JSON for offline review."""
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "digest.json"
    path.write_text(json.dumps(asdict(digest), indent=2, default=str))
    return path
