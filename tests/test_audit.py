"""Tests for src/costdna/audit.py — the dataset-leakage check.

These tests reproduce the failure mode the methodology audit caught on the
Microsoft Azure trace (100% deterministic `deployment_id → subscription_id`)
and the partial leak on Microsoft Philly (85% deterministic `user_id → vc`),
in miniature.
"""

from __future__ import annotations

import pandas as pd
import pytest

from costdna.audit import AuditResult, find_deterministic_edges


def test_azure_pattern_full_determinism():
    """Reproduces the Azure-trace pattern: every deployment_id maps 1:1 to
    a single subscription_id. The audit must flag this as 1.0."""
    df = pd.DataFrame({
        "deployment_id":   ["d1", "d1", "d2", "d2", "d3", "d3"],
        "subscription_id": ["A",  "A",  "B",  "B",  "C",  "C"],
        # A genuinely non-leaking behavioral feature for contrast.
        "cpu_avg":         [0.3,  0.4,  0.5,  0.6,  0.7,  0.8],
    })
    flagged = find_deterministic_edges(
        df, target_col="subscription_id",
        candidate_edge_cols=["deployment_id", "cpu_avg"],
    )
    assert "deployment_id" in flagged
    assert flagged["deployment_id"] == pytest.approx(1.0)
    # cpu_avg has 6 distinct values, each maps to one subscription_id, so it
    # would also be flagged as deterministic. That's the correct behavior —
    # a single-use behavioural feature is a leak in the same sense, and the
    # caller should drop it. Document this in the limitations doc.
    # For this test we just assert deployment_id is flagged, not that
    # cpu_avg isn't.


def test_philly_pattern_partial_determinism():
    """Reproduces the Philly-trace pattern: some users belong to multiple
    virtual clusters, but the majority belong to one. The audit should
    catch this at the default 0.85 threshold."""
    # 5 of 6 users map to a single vc → determinism = 5/6 ≈ 0.833 — just
    # under threshold. 9 of 10 users → 0.9 — flagged.
    df = pd.DataFrame({
        "user_id": ["u1", "u1", "u2", "u2", "u3", "u3",
                    "u4", "u4", "u5", "u5", "u6", "u6",
                    "u7", "u7", "u8", "u8", "u9", "u9",
                    "u10", "u10"],
        "vc":      ["x",  "x",  "y",  "y",  "z",  "z",
                    "x",  "x",  "y",  "y",  "z",  "z",
                    "x",  "x",  "y",  "y",  "z",  "z",
                    "x",  "y"],  # u10 spans two clusters
    })
    flagged = find_deterministic_edges(
        df, target_col="vc", candidate_edge_cols=["user_id"],
    )
    # 9 of 10 users (90%) deterministically map → above 0.85 default.
    assert "user_id" in flagged
    assert flagged["user_id"] == pytest.approx(0.9)


def test_clean_dataset_returns_empty():
    """No leaks → returns empty dict / list.

    Note that a feature whose every distinct value maps to a single target
    (e.g. ["x","x","y","y","z","z"] against ["A","B","A","B","A","B"]) is
    still flagged as deterministic — it IS leaking. The honest "clean"
    case requires a feature that spans multiple targets within each value.
    """
    df2 = pd.DataFrame({
        "target": ["A", "B", "A", "B", "A", "B", "A", "B"],
        "feat":   ["x", "x", "y", "y", "x", "y", "y", "x"],
    })
    flagged = find_deterministic_edges(df2, "target", ["feat"])
    assert flagged == {}


def test_threshold_respected():
    """A column at 0.8 determinism should not be flagged at the default
    0.85, but should be flagged if the threshold is lowered to 0.5.

    Data: 5 distinct edges. 4 deterministically map to one target; 1
    spans two. Determinism = 4/5 = 0.8.
    """
    df = pd.DataFrame({
        "edge":   ["x", "y", "z", "z", "w", "w", "v"],
        "target": ["A", "A", "B", "B", "A", "B", "A"],
    })
    determinism = (df.groupby("edge")["target"].nunique() == 1).mean()
    assert 0.5 < determinism < 0.85, (
        f"test invariant: determinism should be between 0.5 and 0.85, "
        f"got {determinism}"
    )
    assert find_deterministic_edges(df, "target", ["edge"]) == {}
    assert "edge" in find_deterministic_edges(
        df, "target", ["edge"], threshold=0.5
    )


def test_return_full_returns_audit_result_objects():
    df = pd.DataFrame({
        "target": ["A", "A", "B", "B", "C", "C"],
        "edge":   ["x", "x", "y", "y", "z", "z"],
    })
    full = find_deterministic_edges(
        df, "target", ["edge"], return_full=True
    )
    assert isinstance(full, list)
    assert len(full) == 1
    r = full[0]
    assert isinstance(r, AuditResult)
    assert r.column == "edge"
    assert r.determinism == pytest.approx(1.0)
    assert r.n_distinct_values == 3


def test_target_in_candidates_is_silently_skipped():
    """Asking 'is the target deterministic of itself?' is a degenerate
    question; the function silently skips it rather than returning 1.0."""
    df = pd.DataFrame({"target": ["A", "A", "B"], "other": ["x", "x", "y"]})
    flagged = find_deterministic_edges(
        df, "target", ["target", "other"]
    )
    assert "target" not in flagged
    assert "other" in flagged


def test_missing_target_raises():
    df = pd.DataFrame({"a": [1, 2, 3]})
    with pytest.raises(KeyError, match="target_col"):
        find_deterministic_edges(df, "missing", ["a"])


def test_missing_candidate_raises():
    df = pd.DataFrame({"target": ["A", "B", "C"]})
    with pytest.raises(KeyError, match="candidate column"):
        find_deterministic_edges(df, "target", ["nonexistent"])


def test_synthetic_env_is_known_to_fail_its_own_audit():
    """Regression pin for an honest finding: the synthetic env's vpc_cidr and
    iam_role are 1.0-deterministic of team BY CONSTRUCTION (each team owns a
    VPC; role names follow team pools) — the same numeric pattern the project
    called a leak on Azure. The README discloses this; this test makes sure
    the disclosure can never silently drift back to "the checks don't
    trigger" (a claim an earlier README version made, wrongly).
    """
    from costdna import TEAMS
    from costdna.collectors import generate_synthetic_signals

    _, meta, _, _ = generate_synthetic_signals(
        n_per_type_per_team=4, days=3, seed=7)
    labeled = meta[meta["team"].isin(TEAMS)]
    leaks = find_deterministic_edges(
        labeled, target_col="team",
        candidate_edge_cols=["vpc_cidr", "iam_role"],
    )
    assert leaks.get("vpc_cidr") == pytest.approx(1.0)
    assert leaks.get("iam_role") == pytest.approx(1.0)
