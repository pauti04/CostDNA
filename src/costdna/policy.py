"""Governance generator — turn a scan into AWS Organizations enforcement.

Closes the loop from "infer tags" to "prevent future un-tagging":

  1. **Tag policy** — an AWS Organizations tag policy that standardizes the
     `team` tag key and pins its allowed values to the teams CostDNA actually
     found (high-confidence only).
  2. **SCP** — a Service Control Policy that denies *creating* resources
     without the `team` tag, for the services where tag-on-create conditions
     actually work.
  3. **Preview** — the resources that would be flagged as out-of-policy today
     (i.e. the low-confidence ones CostDNA refuses to auto-tag).

Safety posture, matching the rest of the project: **low-confidence
predictions never silently become policy.** Teams are derived only from
predictions at/above the confidence threshold; if nothing clears the bar,
we raise instead of emitting an empty-but-plausible policy.

Honest limitation (documented, not hidden): SCP tag-on-create enforcement
relies on the `aws:RequestTag` condition key, which only some create-APIs
support. EC2 RunInstances, RDS CreateDBInstance, and Lambda CreateFunction
do; **S3 CreateBucket does not** (bucket tags are applied afterward via
PutBucketTagging), so S3 cannot be gated this way and is deliberately
excluded from the generated SCP.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

__all__ = [
    "teams_from_predictions",
    "build_tag_policy",
    "build_require_tag_scp",
    "preview_out_of_policy",
    "PolicyBundle",
    "generate_policies",
]

# Resource types the tag policy's compliance reporting should cover.
# Format is the tag-policy `enforced_for` service:resourcetype syntax.
DEFAULT_ENFORCED_FOR = (
    "ec2:instance",
    "ec2:volume",
    "rds:db",
    "lambda:function",
    "s3:bucket",
)

# Create-actions that honor aws:RequestTag at creation time. S3 CreateBucket
# is intentionally absent — see module docstring.
_SCP_CREATE_ACTIONS = {
    "ec2:RunInstances": ["arn:aws:ec2:*:*:instance/*"],
    "rds:CreateDBInstance": ["arn:aws:rds:*:*:db:*"],
    "lambda:CreateFunction": ["arn:aws:lambda:*:*:function:*"],
}


def teams_from_predictions(
    predictions: pd.DataFrame,
    *,
    min_confidence: float = 0.7,
) -> tuple[list[str], list[str]]:
    """Extract allowed team values from a predictions frame.

    Returns ``(teams, excluded_teams)`` where *teams* come only from rows at
    or above ``min_confidence`` and *excluded_teams* are teams that appear
    **only** in low-confidence rows (worth surfacing: they exist in the
    account, but the model isn't sure enough to bake them into policy).

    Raises
    ------
    ValueError
        If no prediction clears the confidence bar — better to fail loudly
        than emit a policy derived from guesses.
    """
    if "team_pred" not in predictions.columns and "team" in predictions.columns:
        predictions = predictions.rename(columns={"team": "team_pred"})
    high = predictions[predictions["confidence"] >= min_confidence]
    if high.empty:
        raise ValueError(
            f"No predictions at confidence >= {min_confidence}; refusing to "
            "generate a tag policy from low-confidence guesses. Re-run the "
            "scan or lower the threshold deliberately."
        )
    teams = sorted(high["team_pred"].astype(str).unique())
    low_only = sorted(
        set(predictions["team_pred"].astype(str).unique()) - set(teams)
    )
    return teams, low_only


def build_tag_policy(
    teams: list[str],
    *,
    tag_key: str = "team",
    enforced_for: tuple[str, ...] = DEFAULT_ENFORCED_FOR,
) -> dict:
    """AWS Organizations tag policy pinning the tag key + allowed values.

    Uses the tag-policy ``@@assign`` operator syntax. Attach via
    Organizations → Policies → Tag policies (requires tag policies enabled
    on the org).
    """
    if not teams:
        raise ValueError("teams must be non-empty")
    return {
        "tags": {
            tag_key: {
                "tag_key": {"@@assign": tag_key},
                "tag_value": {"@@assign": sorted(teams)},
                "enforced_for": {"@@assign": sorted(enforced_for)},
            }
        }
    }


def build_require_tag_scp(*, tag_key: str = "team") -> dict:
    """SCP denying resource *creation* without the tag, where AWS supports it.

    One Deny statement per create-action, gated on the ``Null`` condition for
    ``aws:RequestTag/<tag_key>`` — the standard require-tag-on-create pattern.
    Only covers actions that honor RequestTag (see module docstring for the
    S3 exception).
    """
    statements = []
    for action, resources in sorted(_SCP_CREATE_ACTIONS.items()):
        service = action.split(":")[0]
        statements.append({
            "Sid": f"Deny{service.capitalize()}CreateWithout{tag_key.capitalize()}Tag",
            "Effect": "Deny",
            "Action": [action],
            "Resource": resources,
            "Condition": {"Null": {f"aws:RequestTag/{tag_key}": "true"}},
        })
    return {"Version": "2012-10-17", "Statement": statements}


def preview_out_of_policy(
    predictions: pd.DataFrame,
    *,
    min_confidence: float = 0.7,
) -> pd.DataFrame:
    """Resources that would be flagged once enforcement lands.

    These are the low-confidence rows: CostDNA won't auto-tag them, so under
    an enforced tag policy they remain untagged/out-of-policy until a human
    confirms them (the active-learning path).
    """
    if "team_pred" not in predictions.columns and "team" in predictions.columns:
        predictions = predictions.rename(columns={"team": "team_pred"})
    low = predictions[predictions["confidence"] < min_confidence]
    return low.sort_values("confidence")[
        [c for c in ("resource_id", "team_pred", "confidence") if c in low.columns]
    ].reset_index(drop=True)


@dataclass
class PolicyBundle:
    """Everything `costdna policy` emits, in one object."""

    tag_policy: dict
    scp: dict
    teams: list[str]
    excluded_teams: list[str] = field(default_factory=list)
    out_of_policy: pd.DataFrame = field(default_factory=pd.DataFrame)


def generate_policies(
    predictions: pd.DataFrame,
    *,
    tag_key: str = "team",
    min_confidence: float = 0.7,
) -> PolicyBundle:
    """One-call pipeline: predictions → tag policy + SCP + preview."""
    teams, excluded = teams_from_predictions(
        predictions, min_confidence=min_confidence
    )
    return PolicyBundle(
        tag_policy=build_tag_policy(teams, tag_key=tag_key),
        scp=build_require_tag_scp(tag_key=tag_key),
        teams=teams,
        excluded_teams=excluded,
        out_of_policy=preview_out_of_policy(
            predictions, min_confidence=min_confidence
        ),
    )
