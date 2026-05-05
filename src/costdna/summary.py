"""Executive summary — the four lines a FinOps engineer actually wants.

Translates predictions into dollars, action recommendations, and a
readable headline. This is what shows up at the top of `costdna scan`
output, before any of the research-y panels.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class ExecutiveSummary:
    total_resources: int
    total_spend: float
    high_conf_resources: int        # confidence >= 0.7
    high_conf_spend: float
    review_resources: int           # confidence < 0.7
    review_spend: float
    by_team: dict[str, tuple[int, float]]  # team -> (n_resources, $)
    actionable_lines: list[str]


def build_summary(
    predictions: list[str],
    confidences: np.ndarray,
    node_ids: list[str],
    signals: pd.DataFrame,
    metadata: pd.DataFrame,
    *,
    high_conf_threshold: float = 0.7,
) -> ExecutiveSummary:
    cost = signals[signals["signal_type"] == "cost"]
    cost_per_rid = cost.groupby("resource_id")["value"].sum().to_dict()

    total_spend = float(sum(cost_per_rid.values()))
    by_team: dict[str, list[float]] = {}
    high_conf = (0, 0.0)
    review = (0, 0.0)

    for rid, team, conf in zip(node_ids, predictions, confidences):
        spend = float(cost_per_rid.get(rid, 0.0))
        by_team.setdefault(team, []).append(spend)
        if conf >= high_conf_threshold:
            high_conf = (high_conf[0] + 1, high_conf[1] + spend)
        else:
            review = (review[0] + 1, review[1] + spend)

    by_team_agg = {t: (len(spends), float(sum(spends))) for t, spends in by_team.items()}

    # Actionable lines — ranked by impact ($).
    lines: list[str] = []
    sorted_teams = sorted(by_team_agg.items(), key=lambda kv: -kv[1][1])
    for team, (n, dollars) in sorted_teams[:3]:
        lines.append(f"Tag {n} resources as {team} → moves ${dollars:,.2f} out of 'untagged'.")
    if review[0] > 0:
        lines.append(f"Review {review[0]} low-confidence resources "
                     f"(${review[1]:,.2f}) before tagging — these need a human eye.")

    return ExecutiveSummary(
        total_resources=len(node_ids),
        total_spend=total_spend,
        high_conf_resources=high_conf[0],
        high_conf_spend=high_conf[1],
        review_resources=review[0],
        review_spend=review[1],
        by_team=by_team_agg,
        actionable_lines=lines,
    )
