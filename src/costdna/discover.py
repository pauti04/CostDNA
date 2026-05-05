"""Team auto-discovery from IAM role naming patterns.

Real AWS environments don't tell you up-front "we have these N teams." The
tool has to find them. This module clusters resources by their IAM role
prefixes — common practice in real envs is `team-purpose-env` or
`purpose-team-env`, with teams sharing tokens.

Approach:
  1. Tokenize every distinct IAM role name (split on - / _ . :).
  2. Score each token by how often it appears as the FIRST or SECOND token
     across many distinct roles — those are likely team identifiers.
  3. Cluster resources by their dominant token.
  4. Each cluster becomes a candidate team.

Output: a mapping from resource_id → discovered_team_name. The names are
just the tokens themselves (e.g., 'etl', 'apigw', 'eks'). The operator can
rename them later via the active-learning loop.
"""

from __future__ import annotations

import re
from collections import Counter

import pandas as pd

_TOKEN_SPLIT = re.compile(r"[-_/.:\s]+")
_STOPWORDS = {
    # Environments
    "prod", "stg", "staging", "dev", "test", "qa", "uat",
    # Sharing/scope
    "shared", "internal", "public", "private", "global", "regional",
    # AWS resource type tokens
    "ec2", "rds", "s3", "ecs", "eks", "lambda", "fn", "function",
    "instance", "bucket", "table", "queue", "topic",
    # IAM verbs/nouns
    "role", "policy", "user", "service", "profile", "execution",
    "writer", "reader", "readonly", "rw", "ro", "admin", "manager",
    # Generic infra terms
    "tier", "cf", "log", "logs", "tooling", "core", "common",
    "default", "main", "primary", "secondary",
    # Single-letter / very short
    "svc", "api", "app", "fn",
}


def _tokens_from_role(role: str) -> list[str]:
    if not role:
        return []
    # Strip ARN prefix if present.
    role = role.split("/")[-1]
    parts = [p.lower() for p in _TOKEN_SPLIT.split(role) if p]
    return [p for p in parts if p and not p.isdigit()]


def discover_teams(
    metadata: pd.DataFrame,
    *,
    min_cluster_size: int = 2,
    max_teams: int = 8,
) -> tuple[dict[str, str], list[str]]:
    """Returns (resource_id → team_name, list_of_discovered_teams).

    Falls back to assigning unmatched resources to 'unassigned'.
    """
    if "iam_role" not in metadata.columns:
        return {rid: "unassigned" for rid in metadata["resource_id"]}, ["unassigned"]

    # Score tokens by how many distinct role names they appear in.
    role_to_tokens: dict[str, list[str]] = {}
    for role in metadata["iam_role"].dropna().unique():
        role_to_tokens[role] = _tokens_from_role(role)

    token_role_count: Counter = Counter()
    for tokens in role_to_tokens.values():
        for t in set(tokens):
            if t in _STOPWORDS:
                continue
            token_role_count[t] += 1

    # Top tokens → candidate team names.
    candidates = [t for t, c in token_role_count.most_common() if c >= min_cluster_size]
    candidates = candidates[:max_teams]
    if not candidates:
        return {rid: "unassigned" for rid in metadata["resource_id"]}, ["unassigned"]

    # Each role gets the highest-ranked candidate token it contains.
    role_to_team: dict[str, str] = {}
    for role, tokens in role_to_tokens.items():
        for cand in candidates:
            if cand in tokens:
                role_to_team[role] = cand
                break
        else:
            role_to_team[role] = "unassigned"

    rid_to_team: dict[str, str] = {}
    for _, row in metadata.iterrows():
        role = row.get("iam_role") or ""
        rid_to_team[row["resource_id"]] = role_to_team.get(role, "unassigned")

    teams_seen = sorted(set(rid_to_team.values()))
    return rid_to_team, teams_seen
