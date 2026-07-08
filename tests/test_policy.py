"""Tests for costdna.policy — the tag-policy / SCP governance generator.

Pins the issue-#3 acceptance criteria, especially the safety one:
low-confidence predictions must never silently become policy.
"""

from __future__ import annotations

import pandas as pd
import pytest

from costdna.policy import (build_require_tag_scp, build_tag_policy,
                            generate_policies, preview_out_of_policy,
                            teams_from_predictions)


def _preds(rows):
    return pd.DataFrame(rows)


def test_teams_only_from_high_confidence():
    df = _preds([
        {"resource_id": "r1", "team_pred": "ml", "confidence": 0.95},
        {"resource_id": "r2", "team_pred": "data", "confidence": 0.71},
        {"resource_id": "r3", "team_pred": "ghost", "confidence": 0.30},  # low-conf only
    ])
    teams, excluded = teams_from_predictions(df)
    assert teams == ["data", "ml"]
    assert excluded == ["ghost"], "teams seen only in low-conf rows must be surfaced, not baked in"


def test_fails_loudly_when_nothing_clears_the_bar():
    df = _preds([
        {"resource_id": "r1", "team_pred": "ml", "confidence": 0.4},
        {"resource_id": "r2", "team_pred": "data", "confidence": 0.6},
    ])
    with pytest.raises(ValueError, match="refusing"):
        teams_from_predictions(df)


def test_legacy_team_column_accepted():
    df = _preds([{"resource_id": "r1", "team": "ml", "confidence": 0.9}])
    teams, _ = teams_from_predictions(df)
    assert teams == ["ml"]


def test_tag_policy_schema_uses_assign_operators():
    pol = build_tag_policy(["ml", "data"], tag_key="team")
    entry = pol["tags"]["team"]
    assert entry["tag_key"] == {"@@assign": "team"}
    assert entry["tag_value"] == {"@@assign": ["data", "ml"]}   # sorted
    assert "ec2:instance" in entry["enforced_for"]["@@assign"]
    assert "s3:bucket" in entry["enforced_for"]["@@assign"]     # reporting covers S3...


def test_scp_denies_creation_without_tag_and_excludes_s3():
    scp = build_require_tag_scp(tag_key="team")
    assert scp["Version"] == "2012-10-17"
    actions = {a for s in scp["Statement"] for a in s["Action"]}
    # ...but the SCP does NOT gate S3 — CreateBucket doesn't honor RequestTag.
    assert actions == {"ec2:RunInstances", "rds:CreateDBInstance", "lambda:CreateFunction"}
    for stmt in scp["Statement"]:
        assert stmt["Effect"] == "Deny"
        assert stmt["Condition"] == {"Null": {"aws:RequestTag/team": "true"}}


def test_scp_custom_tag_key_propagates():
    scp = build_require_tag_scp(tag_key="cost_center")
    for stmt in scp["Statement"]:
        assert "aws:RequestTag/cost_center" in stmt["Condition"]["Null"]


def test_preview_is_exactly_the_low_confidence_rows_sorted():
    df = _preds([
        {"resource_id": "hi", "team_pred": "ml", "confidence": 0.9},
        {"resource_id": "mid", "team_pred": "data", "confidence": 0.65},
        {"resource_id": "lo", "team_pred": "ml", "confidence": 0.30},
    ])
    prev = preview_out_of_policy(df)
    assert list(prev["resource_id"]) == ["lo", "mid"]   # ascending confidence
    assert "hi" not in set(prev["resource_id"])


def test_generate_policies_end_to_end():
    df = _preds([
        {"resource_id": "r1", "team_pred": "ml", "confidence": 0.95},
        {"resource_id": "r2", "team_pred": "data", "confidence": 0.80},
        {"resource_id": "r3", "team_pred": "ml", "confidence": 0.40},
    ])
    bundle = generate_policies(df)
    assert bundle.teams == ["data", "ml"]
    assert bundle.tag_policy["tags"]["team"]["tag_value"]["@@assign"] == ["data", "ml"]
    assert len(bundle.scp["Statement"]) == 3
    assert list(bundle.out_of_policy["resource_id"]) == ["r3"]
