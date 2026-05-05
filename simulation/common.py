"""Shared helpers for the team workload simulators.

Each simulator generates per-team CloudTrail events by *assuming* the team's
IAM role before making API calls. Without this, every event has the same
userIdentity (yours), and CostDNA's behavioral signal evaporates.

Setup expectation:
  - Terraform applied with the per-team IAM roles + cross-account-trust policy
  - Your local AWS profile has sts:AssumeRole permission on those roles
    (which it does if you're an admin / root user)
"""

from __future__ import annotations

import csv
import os
from functools import lru_cache
from pathlib import Path

import boto3

LABELS_PATH = Path(__file__).resolve().parent.parent / "labels.csv"

# Maps the team name (matching costdna.TEAMS) to the IAM role suffix used by
# the Terraform in this repo (terraform/variables.tf).
TEAM_ROLE = {
    "backend":  "backend-svc-role",
    "data":     "data-pipeline-role",
    "ml":       "ml-training-role",
    "platform": "platform-infra-role",
}


@lru_cache(maxsize=1)
def _account_id() -> str:
    return boto3.client("sts").get_caller_identity()["Account"]


def assumed_session(team: str, region: str | None = None) -> boto3.Session:
    """Returns a boto3 session whose credentials belong to `team`'s IAM role.

    Every API call made through this session will be logged in CloudTrail
    with the team's role as the userIdentity — that's the per-team
    behavioral signal CostDNA needs.
    """
    region = region or os.environ.get("AWS_REGION", "us-east-1")
    role_suffix = TEAM_ROLE[team]
    role_arn = f"arn:aws:iam::{_account_id()}:role/{role_suffix}"
    sts = boto3.client("sts", region_name=region)
    creds = sts.assume_role(
        RoleArn=role_arn,
        RoleSessionName=f"costdna-sim-{team}",
        DurationSeconds=3600,
    )["Credentials"]
    return boto3.Session(
        aws_access_key_id=creds["AccessKeyId"],
        aws_secret_access_key=creds["SecretAccessKey"],
        aws_session_token=creds["SessionToken"],
        region_name=region,
    )


def load_labels(team: str) -> dict[str, list[str]]:
    """Read labels.csv (terraform-generated ground truth) and return
    {resource_type: [resource_id, ...]} for the given team."""
    if not LABELS_PATH.exists():
        raise FileNotFoundError(
            f"{LABELS_PATH} not found — run `terraform apply` first."
        )
    out: dict[str, list[str]] = {"ec2": [], "rds": [], "lambda": [], "s3": []}
    with open(LABELS_PATH) as f:
        for row in csv.DictReader(f):
            if row["team"] != team:
                continue
            rid = row["resource_id"]
            if rid.startswith("i-"):
                out["ec2"].append(rid)
            elif "fn" in rid:
                out["lambda"].append(rid)
            elif "costdna-synth" in rid and "lambda" not in rid:
                if len(rid.split("-")) > 3:
                    out["s3"].append(rid)
                else:
                    out["rds"].append(rid)
    return out


def maybe(prob: float, rng) -> bool:
    return rng.random() < prob
