"""Tests for costdna.drift.compute_drift — the `costdna diff` core."""

from __future__ import annotations

import pandas as pd

from costdna.drift import compute_drift


def _preds(rows):
    return pd.DataFrame(rows)


def test_same_team_is_not_drift():
    old = _preds([{"resource_id": "r1", "team_pred": "ml", "confidence": 0.9}])
    new = _preds([{"resource_id": "r1", "team_pred": "ml", "confidence": 0.95}])
    assert compute_drift(old, new) == []


def test_changed_team_is_drift():
    old = _preds([{"resource_id": "r1", "team_pred": "ml", "confidence": 0.95}])
    new = _preds([{"resource_id": "r1", "team_pred": "data", "confidence": 0.92}])
    events = compute_drift(old, new)
    assert len(events) == 1
    e = events[0]
    assert e.old_team == "ml" and e.new_team == "data"


def test_severity_thresholds():
    old = _preds([
        {"resource_id": "maj", "team_pred": "ml", "confidence": 0.95},
        {"resource_id": "min", "team_pred": "ml", "confidence": 0.80},
        {"resource_id": "low", "team_pred": "ml", "confidence": 0.60},
    ])
    new = _preds([
        {"resource_id": "maj", "team_pred": "data", "confidence": 0.92},  # both ≥0.9 → major
        {"resource_id": "min", "team_pred": "data", "confidence": 0.75},  # min in [0.7,0.9) → minor
        {"resource_id": "low", "team_pred": "data", "confidence": 0.95},  # min <0.7 → low_confidence
    ])
    sev = {e.resource_id: e.severity for e in compute_drift(old, new)}
    assert sev == {"maj": "major", "min": "minor", "low": "low_confidence"}


def test_resources_only_in_one_frame_are_dropped():
    old = _preds([
        {"resource_id": "keep", "team_pred": "ml", "confidence": 0.9},
        {"resource_id": "removed", "team_pred": "ml", "confidence": 0.9},
    ])
    new = _preds([
        {"resource_id": "keep", "team_pred": "data", "confidence": 0.9},
        {"resource_id": "added", "team_pred": "data", "confidence": 0.9},
    ])
    ids = {e.resource_id for e in compute_drift(old, new)}
    assert ids == {"keep"}  # removed/added are not drift


def test_sorted_major_first_then_by_cost():
    old = _preds([
        {"resource_id": "cheap_major", "team_pred": "ml", "confidence": 0.95, "cost": 10.0},
        {"resource_id": "rich_major", "team_pred": "ml", "confidence": 0.95, "cost": 500.0},
        {"resource_id": "minor", "team_pred": "ml", "confidence": 0.80, "cost": 9999.0},
    ])
    new = _preds([
        {"resource_id": "cheap_major", "team_pred": "data", "confidence": 0.95, "cost": 10.0},
        {"resource_id": "rich_major", "team_pred": "data", "confidence": 0.95, "cost": 500.0},
        {"resource_id": "minor", "team_pred": "data", "confidence": 0.80, "cost": 9999.0},
    ])
    order = [e.resource_id for e in compute_drift(old, new)]
    # majors first (by cost desc), then the minor — even though minor has the highest cost.
    assert order == ["rich_major", "cheap_major", "minor"]


def test_no_confidence_columns_defaults_to_zero_low_confidence():
    old = _preds([{"resource_id": "r1", "team_pred": "ml"}])
    new = _preds([{"resource_id": "r1", "team_pred": "data"}])
    events = compute_drift(old, new)
    assert len(events) == 1
    assert events[0].severity == "low_confidence"  # missing conf → 0 → below threshold
