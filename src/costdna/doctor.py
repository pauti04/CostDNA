"""Preflight checks for live AWS scans.

Catches the reasons a `costdna scan --aws-profile prod` will fail BEFORE it
runs — IAM permissions, missing log groups, empty CloudTrail, no resources,
no Cost Explorer access. Each check returns (status, message) so the doctor
output is a clear punchlist.

Idempotent and read-only. Safe to run any time.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable

log = logging.getLogger(__name__)


@dataclass
class Check:
    name: str
    status: str        # 'ok' / 'warn' / 'fail'
    message: str
    fix_hint: str = ""


def _try(name: str, fn: Callable[[], Check]) -> Check:
    try:
        return fn()
    except Exception as e:
        return Check(name=name, status="fail", message=str(e),
                     fix_hint="Check IAM permissions and that the resource exists.")


def _check_credentials(session) -> Check:
    sts = session.client("sts")
    ident = sts.get_caller_identity()
    return Check(
        name="AWS credentials",
        status="ok",
        message=f"authenticated as {ident.get('Arn', '?')}",
    )


def _check_resources(session) -> Check:
    ec2 = session.client("ec2")
    n_ec2 = sum(len(res["Instances"]) for page in
                ec2.get_paginator("describe_instances").paginate()
                for res in page["Reservations"])
    rds = session.client("rds")
    n_rds = sum(len(p["DBInstances"]) for p in
                rds.get_paginator("describe_db_instances").paginate())
    s3 = session.client("s3")
    n_s3 = len(s3.list_buckets().get("Buckets", []))
    lam = session.client("lambda")
    n_lam = sum(len(p["Functions"]) for p in
                lam.get_paginator("list_functions").paginate())
    total = n_ec2 + n_rds + n_s3 + n_lam
    if total == 0:
        return Check(name="Resources",
                     status="fail",
                     message="no EC2/RDS/Lambda/S3 resources found in this account",
                     fix_hint="Either run `terraform apply` to populate the synthetic env, "
                              "or run against an account that has resources.")
    if total < 5:
        return Check(name="Resources", status="warn",
                     message=f"only {total} resources found ({n_ec2} EC2, "
                             f"{n_rds} RDS, {n_lam} Lambda, {n_s3} S3)",
                     fix_hint="Model needs ≥10 resources for stable training.")
    return Check(name="Resources", status="ok",
                 message=f"{total} resources ({n_ec2} EC2, {n_rds} RDS, "
                         f"{n_lam} Lambda, {n_s3} S3)")


def _check_cloudtrail(session) -> Check:
    ct = session.client("cloudtrail")
    trails = ct.describe_trails().get("trailList", [])
    if not trails:
        return Check(name="CloudTrail", status="fail",
                     message="no trails configured in this account",
                     fix_hint="Enable a CloudTrail log → Console → CloudTrail → Create trail.")
    # Try a tiny lookup to confirm we have read permission.
    try:
        end = datetime.now(timezone.utc)
        start = end - timedelta(hours=1)
        ct.lookup_events(StartTime=start, EndTime=end, MaxResults=1)
        return Check(name="CloudTrail", status="ok",
                     message=f"{len(trails)} trail(s) configured, lookup_events works")
    except Exception as e:
        return Check(name="CloudTrail", status="warn",
                     message=f"trails exist but lookup failed: {e}",
                     fix_hint="Add cloudtrail:LookupEvents to your IAM role.")


def _check_flow_logs(session) -> Check:
    logs = session.client("logs")
    try:
        groups = logs.describe_log_groups(
            logGroupNamePrefix="/aws/vpc/flowlogs",
        ).get("logGroups", [])
        if not groups:
            return Check(name="VPC Flow Logs", status="warn",
                         message="no log group at /aws/vpc/flowlogs",
                         fix_hint="The default name in CostDNA's collector. Either rename "
                                  "your log group, or pass --flow-log-group on scan.")
        return Check(name="VPC Flow Logs", status="ok",
                     message=f"log group /aws/vpc/flowlogs exists "
                             f"({groups[0].get('storedBytes', 0):,} bytes stored)")
    except Exception as e:
        return Check(name="VPC Flow Logs", status="warn",
                     message=str(e),
                     fix_hint="Add logs:DescribeLogGroups to your IAM role.")


def _check_cost_explorer(session) -> Check:
    ce = session.client("ce", region_name="us-east-1")
    try:
        end = datetime.now(timezone.utc).date()
        start = end - timedelta(days=1)
        ce.get_cost_and_usage(
            TimePeriod={"Start": start.isoformat(), "End": end.isoformat()},
            Granularity="DAILY",
            Metrics=["UnblendedCost"],
        )
        return Check(name="Cost Explorer", status="ok",
                     message="cost data accessible")
    except Exception as e:
        msg = str(e)
        if "not enabled" in msg.lower():
            return Check(name="Cost Explorer", status="fail",
                         message="Cost Explorer not enabled on this account",
                         fix_hint="Enable in Console → Billing → Cost Explorer "
                                  "(takes ~24h to populate).")
        return Check(name="Cost Explorer", status="warn",
                     message=msg,
                     fix_hint="Add ce:GetCostAndUsage to your IAM role.")


def run_doctor(profile: str | None = None, region: str = "us-east-1") -> list[Check]:
    """Run all checks and return them in display order."""
    import boto3
    session = boto3.Session(profile_name=profile, region_name=region)
    return [
        _try("AWS credentials", lambda: _check_credentials(session)),
        _try("Resources",       lambda: _check_resources(session)),
        _try("CloudTrail",      lambda: _check_cloudtrail(session)),
        _try("VPC Flow Logs",   lambda: _check_flow_logs(session)),
        _try("Cost Explorer",   lambda: _check_cost_explorer(session)),
    ]
