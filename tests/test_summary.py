"""Tests for costdna.summary.build_summary — the exec-summary $ rollup."""

from __future__ import annotations

import numpy as np
import pandas as pd

from costdna.summary import build_summary


def _signals(cost_by_rid: dict[str, float]) -> pd.DataFrame:
    rows = [{"resource_id": rid, "signal_type": "cost", "value": v}
            for rid, v in cost_by_rid.items()]
    # add some non-cost noise that must be ignored
    rows.append({"resource_id": "r1", "signal_type": "cloudtrail_event", "value": 1})
    return pd.DataFrame(rows)


def test_totals_and_high_conf_split():
    node_ids = ["r1", "r2", "r3"]
    preds = ["ml", "ml", "data"]
    confs = np.array([0.95, 0.60, 0.99])          # r2 is low-confidence
    signals = _signals({"r1": 100.0, "r2": 50.0, "r3": 30.0})
    meta = pd.DataFrame({"resource_id": node_ids})

    s = build_summary(preds, confs, node_ids, signals, meta)

    assert s.total_resources == 3
    assert s.total_spend == 180.0
    # high-conf = r1 + r3 (0.95, 0.99); review = r2 (0.60)
    assert s.high_conf_resources == 2
    assert s.high_conf_spend == 130.0
    assert s.review_resources == 1
    assert s.review_spend == 50.0


def test_by_team_aggregation():
    node_ids = ["r1", "r2", "r3"]
    preds = ["ml", "ml", "data"]
    confs = np.array([0.9, 0.9, 0.9])
    signals = _signals({"r1": 100.0, "r2": 50.0, "r3": 30.0})
    meta = pd.DataFrame({"resource_id": node_ids})

    s = build_summary(preds, confs, node_ids, signals, meta)
    assert s.by_team["ml"] == (2, 150.0)
    assert s.by_team["data"] == (1, 30.0)


def test_actionable_lines_ranked_by_dollars_and_review_line():
    node_ids = ["r1", "r2", "r3", "r4"]
    preds = ["ml", "data", "backend", "ml"]
    confs = np.array([0.9, 0.9, 0.9, 0.5])        # r4 low-conf
    signals = _signals({"r1": 10.0, "r2": 500.0, "r3": 50.0, "r4": 5.0})
    meta = pd.DataFrame({"resource_id": node_ids})

    s = build_summary(preds, confs, node_ids, signals, meta)
    # data has the most $ (500) so its tag-line comes first
    assert "as data" in s.actionable_lines[0]
    # a review line must be present because r4 is low-confidence
    assert any("low-confidence" in ln for ln in s.actionable_lines)


def test_resource_with_no_cost_counts_as_zero():
    node_ids = ["r1", "r2"]
    preds = ["ml", "ml"]
    confs = np.array([0.9, 0.9])
    signals = _signals({"r1": 100.0})            # r2 has no cost row
    meta = pd.DataFrame({"resource_id": node_ids})

    s = build_summary(preds, confs, node_ids, signals, meta)
    assert s.total_spend == 100.0
    assert s.by_team["ml"] == (2, 100.0)         # 2 resources, $100 total


def test_no_review_line_when_all_high_confidence():
    node_ids = ["r1", "r2"]
    preds = ["ml", "data"]
    confs = np.array([0.95, 0.95])
    signals = _signals({"r1": 10.0, "r2": 20.0})
    meta = pd.DataFrame({"resource_id": node_ids})

    s = build_summary(preds, confs, node_ids, signals, meta)
    assert s.review_resources == 0
    assert not any("low-confidence" in ln for ln in s.actionable_lines)
