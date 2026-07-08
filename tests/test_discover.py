"""Tests for costdna.discover.discover_teams — IAM-role team auto-discovery."""

from __future__ import annotations

import pandas as pd

from costdna.discover import _tokens_from_role, discover_teams


def test_tokenizer_strips_arn_and_env_and_digits():
    toks = _tokens_from_role("arn:aws:iam::123:role/etl-runner-role-01")
    assert "etl" in toks and "runner" in toks
    assert "01" not in toks            # pure digits dropped
    assert "123" not in toks


def test_discovers_team_tokens_from_role_prefixes():
    # Two teams, each appearing in ≥2 distinct role names.
    meta = pd.DataFrame({
        "resource_id": ["r1", "r2", "r3", "r4"],
        "iam_role": [
            "etl-runner-role",
            "etl-glue-execution",
            "apigw-lambda-rest",
            "apigw-ec2-web",
        ],
    })
    rid_to_team, teams = discover_teams(meta, min_cluster_size=2)
    assert rid_to_team["r1"] == "etl"
    assert rid_to_team["r2"] == "etl"
    assert rid_to_team["r3"] == "apigw"
    assert rid_to_team["r4"] == "apigw"
    assert set(teams) == {"etl", "apigw"}


def test_stopwords_are_not_team_names():
    # Every role shares only stopword tokens (prod, role, s3, ...) → no team.
    meta = pd.DataFrame({
        "resource_id": ["r1", "r2"],
        "iam_role": ["prod-s3-role", "prod-rds-role"],
    })
    rid_to_team, teams = discover_teams(meta, min_cluster_size=2)
    assert teams == ["unassigned"]
    assert all(v == "unassigned" for v in rid_to_team.values())


def test_missing_iam_role_column_falls_back_to_unassigned():
    meta = pd.DataFrame({"resource_id": ["r1", "r2"]})
    rid_to_team, teams = discover_teams(meta)
    assert teams == ["unassigned"]
    assert rid_to_team == {"r1": "unassigned", "r2": "unassigned"}


def test_min_cluster_size_filters_singletons():
    # 'etl' appears in 2 roles; 'oneoff' in only 1 → only etl becomes a team.
    meta = pd.DataFrame({
        "resource_id": ["r1", "r2", "r3"],
        "iam_role": ["etl-runner", "etl-glue", "oneoff-thing"],
    })
    rid_to_team, teams = discover_teams(meta, min_cluster_size=2)
    assert rid_to_team["r1"] == "etl"
    assert rid_to_team["r2"] == "etl"
    assert rid_to_team["r3"] == "unassigned"    # singleton token, below min_cluster_size


def test_max_teams_caps_the_count():
    # 5 distinct team tokens, each in 2 roles; cap at 3.
    roles = []
    rids = []
    for i, tok in enumerate(["alpha", "beta", "gamma", "delta", "omega"]):
        roles += [f"{tok}-runner", f"{tok}-worker"]
        rids += [f"r{i}a", f"r{i}b"]
    meta = pd.DataFrame({"resource_id": rids, "iam_role": roles})
    _, teams = discover_teams(meta, min_cluster_size=2, max_teams=3)
    # at most 3 real teams (+ possibly 'unassigned' for the ones that didn't make the cut)
    real = [t for t in teams if t != "unassigned"]
    assert len(real) <= 3
