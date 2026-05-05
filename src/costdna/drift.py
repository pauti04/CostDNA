"""Drift detection — diff two saved scans.

When a team reorgs, ownership changes. When a resource gets repurposed, its
behavior shifts. Either way, what was once high-confidence team X now might
be team Y. Drift detection catches this.

Inputs: two `predictions.csv` files (output of `costdna scan --save-dir`).
Output: a list of resources whose predicted team changed, with the size of
the cost shift each change represents.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class DriftEvent:
    resource_id: str
    old_team: str
    new_team: str
    old_confidence: float
    new_confidence: float
    old_cost: float          # cost in window of old run (if available)
    new_cost: float
    severity: str            # 'major' / 'minor' / 'low_confidence'


def compute_drift(
    old: pd.DataFrame,
    new: pd.DataFrame,
    *,
    confidence_threshold: float = 0.7,
) -> list[DriftEvent]:
    """Compare two predictions DataFrames, returning resources with changed teams.

    Drops resources only present in one frame (those are added/removed, not drifted).
    """
    merged = old.merge(
        new, on="resource_id", suffixes=("_old", "_new"), how="inner",
    )
    events: list[DriftEvent] = []
    for _, r in merged.iterrows():
        if r["team_pred_old"] == r["team_pred_new"]:
            continue
        co = float(r.get("confidence_old", 0))
        cn = float(r.get("confidence_new", 0))
        cost_o = float(r.get("cost_old", 0)) if "cost_old" in r else 0.0
        cost_n = float(r.get("cost_new", 0)) if "cost_new" in r else 0.0

        if min(co, cn) < confidence_threshold:
            severity = "low_confidence"
        elif min(co, cn) >= 0.9:
            severity = "major"
        else:
            severity = "minor"

        events.append(DriftEvent(
            resource_id=str(r["resource_id"]),
            old_team=str(r["team_pred_old"]),
            new_team=str(r["team_pred_new"]),
            old_confidence=co,
            new_confidence=cn,
            old_cost=cost_o,
            new_cost=cost_n,
            severity=severity,
        ))
    events.sort(key=lambda e: (
        {"major": 0, "minor": 1, "low_confidence": 2}[e.severity],
        -(e.old_cost + e.new_cost),
    ))
    return events
