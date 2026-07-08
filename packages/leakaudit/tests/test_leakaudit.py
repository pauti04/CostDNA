"""Tests for leakaudit — mirrors the two real Microsoft case studies in miniature."""

from __future__ import annotations

import pandas as pd
import pytest

import leakaudit
from leakaudit import check, determinism_score, find_deterministic_edges


def test_azure_total_leak():
    """Azure pattern: deployment_id maps 1:1 to subscription_id → determinism 1.0."""
    df = pd.DataFrame({
        "deployment_id":   ["d1", "d1", "d2", "d2", "d3", "d3"],
        "subscription_id": ["A",  "A",  "B",  "B",  "C",  "C"],
        "cpu_bucket":      ["lo", "hi", "lo", "hi", "lo", "hi"],  # spans subs — clean
    })
    assert determinism_score(df, "deployment_id", "subscription_id") == pytest.approx(1.0)
    leaks = find_deterministic_edges(df, "subscription_id", ["deployment_id", "cpu_bucket"])
    assert leaks == {"deployment_id": 1.0}


def test_philly_partial_leak():
    """Philly pattern: ~85% of users belong to one virtual cluster."""
    rows = []
    for u in range(1, 10):                      # 9 users, single-cluster
        rows += [{"user_id": f"u{u}", "vc": ["x", "y", "z"][u % 3]}] * 2
    rows += [{"user_id": "u10", "vc": "x"}, {"user_id": "u10", "vc": "y"}]  # 1 spans
    df = pd.DataFrame(rows)
    assert determinism_score(df, "user_id", "vc") == pytest.approx(0.9)
    assert "user_id" in find_deterministic_edges(df, "vc", ["user_id"])       # default 0.85


def test_clean_column_not_flagged():
    df = pd.DataFrame({"target": ["A", "B"] * 4,
                       "feat":   ["x", "x", "y", "y", "x", "y", "y", "x"]})
    assert find_deterministic_edges(df, "target", ["feat"]) == {}


def test_threshold_respected():
    # 4 of 5 distinct edges map to one target → 0.8; below default 0.85.
    df = pd.DataFrame({"edge":   ["x", "y", "z", "z", "w", "w", "v"],
                       "target": ["A", "A", "B", "B", "A", "B", "A"]})
    assert find_deterministic_edges(df, "target", ["edge"]) == {}
    assert "edge" in find_deterministic_edges(df, "target", ["edge"], threshold=0.5)


def test_check_audits_all_columns_and_reports():
    df = pd.DataFrame({
        "label":  ["A", "A", "B", "B"],
        "leak":   ["p", "p", "q", "q"],   # 1:1 with label
        "clean":  ["m", "n", "m", "n"],   # spans labels
    })
    report = check(df, "label")
    assert not report.clean
    assert "leak" in report.leaks
    assert "clean" not in report.leaks
    # sorted worst-first
    assert report.columns[0].column == "leak"
    assert "LEAK" in str(report)


def test_check_clean_dataset():
    df = pd.DataFrame({"label": ["A", "B", "A", "B"],
                       "f": ["m", "n", "n", "m"]})
    report = check(df, "label")
    assert report.clean
    assert "clean" in str(report)


def test_high_cardinality_flag():
    # Every value unique → 1:1 by construction, but flagged high-cardinality.
    df = pd.DataFrame({"id": [f"r{i}" for i in range(10)],
                       "label": [f"t{i}" for i in range(10)]})
    report = check(df, "label")
    idcol = next(c for c in report.columns if c.column == "id")
    assert idcol.high_cardinality is True


def test_target_missing_raises():
    with pytest.raises(KeyError):
        check(pd.DataFrame({"a": [1]}), "missing")


def test_public_api_surface():
    assert hasattr(leakaudit, "check")
    assert hasattr(leakaudit, "find_deterministic_edges")
    assert leakaudit.__version__
