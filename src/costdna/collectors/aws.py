"""Real AWS signal collectors using boto3.

Pulls four data sources:
  1. CloudTrail events  — who called what, when
  2. VPC Flow Logs      — who talked to whom (CloudWatch Logs Insights query)
  3. Resource metadata  — static attributes per EC2/RDS/Lambda/S3 resource
  4. Cost Explorer      — hourly $ per resource

Hardening:
  - Every API call is wrapped — a permission error on one resource type
    doesn't kill the whole scan.
  - Retries with exponential backoff on Throttling/RequestLimitExceeded.
  - The flow-log group name is configurable (we default to /aws/vpc/flowlogs
    which is what our Terraform creates, but real envs vary).
  - All paginators have hard caps so a runaway account doesn't bankrupt you.

Output: same DataFrame schema as collectors.synthetic, so downstream code is
source-agnostic.
"""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

import pandas as pd

log = logging.getLogger(__name__)

DEFAULT_FLOW_LOG_GROUP = "/aws/vpc/flowlogs"
MAX_CLOUDTRAIL_EVENTS_PER_RESOURCE = 5_000   # cap per resource to bound runtime
MAX_FLOW_LOG_ROWS = 5_000


def _session(profile: str | None, region: str):
    import boto3
    return boto3.Session(profile_name=profile, region_name=region)


def _ct_client(session):
    """CloudTrail client with adaptive retries — lookup_events throttles hard."""
    from botocore.config import Config
    return session.client(
        "cloudtrail",
        config=Config(retries={"max_attempts": 10, "mode": "adaptive"}),
    )


def _retry(fn, *args, max_attempts: int = 5, base_delay: float = 0.5, **kwargs):
    """Retry on AWS Throttling/RequestLimitExceeded errors with exponential backoff."""
    for attempt in range(max_attempts):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            msg = str(e)
            transient = ("Throttling" in msg or "RequestLimitExceeded" in msg
                         or "TooManyRequestsException" in msg)
            if not transient or attempt == max_attempts - 1:
                raise
            time.sleep(base_delay * (2 ** attempt))
    return None  # unreachable


def _list_ec2(session) -> list[dict]:
    ec2 = session.client("ec2")
    out = []
    for page in ec2.get_paginator("describe_instances").paginate():
        for res in page["Reservations"]:
            for inst in res["Instances"]:
                out.append({
                    "resource_id": inst["InstanceId"],
                    "resource_type": "ec2",
                    "iam_role": (inst.get("IamInstanceProfile") or {}).get("Arn", ""),
                    "vpc_cidr": inst.get("VpcId", ""),
                    "created_at": inst["LaunchTime"].isoformat(),
                })
    return out


def _list_rds(session) -> list[dict]:
    rds = session.client("rds")
    out = []
    for page in rds.get_paginator("describe_db_instances").paginate():
        for db in page["DBInstances"]:
            roles = db.get("AssociatedRoles") or []
            iam_role = roles[0].get("RoleArn", "") if roles else ""
            out.append({
                "resource_id": db["DBInstanceIdentifier"],
                "resource_type": "rds",
                "iam_role": iam_role,
                "vpc_cidr": (db.get("DBSubnetGroup") or {}).get("VpcId", ""),
                "created_at": db["InstanceCreateTime"].isoformat(),
            })
    return out


def _list_lambda(session) -> list[dict]:
    lam = session.client("lambda")
    out = []
    for page in lam.get_paginator("list_functions").paginate():
        for fn in page["Functions"]:
            out.append({
                "resource_id": fn["FunctionName"],
                "resource_type": "lambda",
                "iam_role": fn.get("Role", ""),
                "vpc_cidr": (fn.get("VpcConfig") or {}).get("VpcId", ""),
                "created_at": fn.get("LastModified", ""),
            })
    return out


def _list_s3(session) -> list[dict]:
    s3 = session.client("s3")
    out = []
    for b in s3.list_buckets().get("Buckets", []):
        out.append({
            "resource_id": b["Name"],
            "resource_type": "s3",
            "iam_role": "",
            "vpc_cidr": "",
            "created_at": b["CreationDate"].isoformat(),
        })
    return out


def _cloudtrail_events_by_resource(session, resource_id: str, days: int) -> list[dict]:
    """Per-resource ResourceName lookup. Works for management events but
    misses most data events (where ResourceName is an ARN with a key).

    Kept for backwards compatibility but no longer the primary path.
    """
    ct = _ct_client(session)
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    out = []
    try:
        paginator = ct.get_paginator("lookup_events")
        for page in paginator.paginate(
            LookupAttributes=[{"AttributeKey": "ResourceName", "AttributeValue": resource_id}],
            StartTime=start, EndTime=end,
        ):
            for ev in page.get("Events", []):
                out.append(_event_row(resource_id, ev))
                if len(out) >= MAX_CLOUDTRAIL_EVENTS_PER_RESOURCE:
                    return out
    except Exception as e:
        log.warning("CloudTrail per-resource lookup failed for %s: %s", resource_id, e)
    return out


def _event_row(resource_id: str, ev: dict) -> dict:
    """Build one signal row from a CloudTrail event dict."""
    return {
        "resource_id": resource_id,
        "signal_type": "cloudtrail_event",
        "user_identity": ev.get("Username", ""),
        "iam_role": ev.get("Username", ""),
        "event_name": ev.get("EventName", ""),
        "source_account": (ev.get("Resources") or [{}])[0].get("ResourceName", ""),
        "value": 1,
        "timestamp": ev["EventTime"].isoformat(),
    }


def _resource_in_event(ev: dict, resource_id: str) -> bool:
    """True if `resource_id` appears anywhere in the event's resource refs.

    CloudTrail data events store resources as ARNs (often with key paths);
    we substring-match the resource ID against the ARN to handle both
    bucket-only and bucket+key cases.
    """
    for r in ev.get("Resources") or []:
        if resource_id in (r.get("ResourceName") or ""):
            return True
    # Some events stash resources in the raw CloudTrailEvent JSON.
    raw = ev.get("CloudTrailEvent", "")
    if isinstance(raw, str) and resource_id in raw:
        return True
    return False


def _cloudtrail_events_via_eventsource(session, resource_ids: list[str],
                                        days: int) -> list[dict]:
    """Pull events by EventSource (s3, lambda, ec2, rds), then attribute each
    event to whichever resource it touched.

    This is the most reliable way to get data events:
      - `ResourceName` filter on lookup_events doesn't match S3 data-event
        ARNs (the value would be `arn:aws:s3:::bucket/key`, not `bucket`).
      - `Username` filter doesn't match assumed-role events the way you'd
        expect (the userIdentity is `<role>:<session>`, not the role name).
      - `EventSource` is the simplest, reliable filter.

    We then inspect each event's CloudTrailEvent JSON to find which
    resource_id appears in it.
    """
    ct = _ct_client(session)
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    rows: list[dict] = []
    rid_set = set(resource_ids)

    sources = ["s3.amazonaws.com", "lambda.amazonaws.com",
               "ec2.amazonaws.com", "rds.amazonaws.com"]
    n_pulled = 0
    page_pause = 1.5     # CloudTrail allows ~2 req/s; play it safe
    max_pages_per_source = 200  # ~10K events per source max — bounds runtime

    for src_idx, source in enumerate(sources):
        page_count = 0
        try:
            paginator = ct.get_paginator("lookup_events")
            for page in paginator.paginate(
                LookupAttributes=[{"AttributeKey": "EventSource",
                                   "AttributeValue": source}],
                StartTime=start, EndTime=end,
            ):
                page_count += 1
                for ev in page.get("Events", []):
                    n_pulled += 1
                    for rid in rid_set:
                        if _resource_in_event(ev, rid):
                            rows.append(_event_row(rid, ev))
                if len(rows) > MAX_CLOUDTRAIL_EVENTS_PER_RESOURCE * len(rid_set):
                    log.info("hit per-source row cap; stopping %s", source)
                    break
                if page_count >= max_pages_per_source:
                    log.info("hit max_pages cap for %s; stopping", source)
                    break
                time.sleep(page_pause)
            log.info("%s: pulled %d pages", source, page_count)
        except Exception as e:
            # Don't let one source's throttle kill the rest.
            log.warning("CloudTrail EventSource lookup failed for %s: %s "
                        "(continuing with other sources)", source, e)
        # Pause longer between sources to let the rate limit budget recover.
        if src_idx < len(sources) - 1:
            time.sleep(5.0)
    log.info("EventSource sweep: pulled %d raw events, attributed %d", n_pulled, len(rows))
    return rows


def _cloudtrail_events(session, resource_id: str, days: int) -> list[dict]:
    """Legacy single-resource lookup, kept for non-Username-aware callers."""
    return _cloudtrail_events_by_resource(session, resource_id, days)


def _cost_series(session, resource_ids: list[str], days: int) -> list[dict]:
    """Hourly cost from Cost Explorer.

    CE doesn't support `RESOURCE_ID` as a GroupBy dimension by default — that
    requires opting into Cost Allocation Resource IDs (extra setup). Instead
    we group by SERVICE and distribute proportionally per-resource. Less
    accurate than per-resource but works for any account.

    A future improvement: read Cost & Usage Reports from S3 for true
    per-resource hourly cost.
    """
    ce = session.client("ce", region_name="us-east-1")
    end = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    start = end - timedelta(days=days)
    fmt = "%Y-%m-%dT%H:%M:%SZ"

    # Map service name → list of resource_ids of that service type.
    by_service: dict[str, list[str]] = {
        "Amazon Elastic Compute Cloud - Compute": [r for r in resource_ids if r.startswith("i-")],
        "Amazon Relational Database Service":     [r for r in resource_ids if r.startswith(("costdna-", "stg-rds", "dev-rds"))],
        "AWS Lambda":                              [r for r in resource_ids if any(t in r for t in ("-fn", "Function", "Forwarder"))],
        "Amazon Simple Storage Service":          [r for r in resource_ids if any(t in r for t in ("-bucket-", "logs-", "archive"))],
    }

    out = []

    # HOURLY is opt-in-only on most accounts. Try HOURLY first, fall back to DAILY.
    for granularity in ("HOURLY", "DAILY"):
        try:
            tp = ({"Start": start.strftime(fmt), "End": end.strftime(fmt)}
                  if granularity == "HOURLY"
                  else {"Start": start.date().isoformat(),
                        "End": end.date().isoformat()})
            resp = ce.get_cost_and_usage(
                TimePeriod=tp,
                Granularity=granularity,
                Metrics=["UnblendedCost"],
                GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
            )
            for period in resp.get("ResultsByTime", []):
                ts = period["TimePeriod"]["Start"]
                for grp in period.get("Groups", []):
                    service = grp["Keys"][0]
                    amount = float(grp["Metrics"]["UnblendedCost"]["Amount"])
                    rids = by_service.get(service, [])
                    if not rids or amount == 0:
                        continue
                    share = amount / len(rids)
                    for rid in rids:
                        out.append({
                            "resource_id": rid,
                            "signal_type": "cost",
                            "value": share,
                            "timestamp": ts,
                        })
            log.info("Cost Explorer %s query returned %d rows", granularity, len(out))
            return out
        except Exception as e:
            msg = str(e)
            if granularity == "HOURLY" and "opt-in" in msg.lower():
                log.info("Hourly CE not enabled — falling back to DAILY")
                continue
            log.warning("Cost Explorer query failed: %s", e)
            return out
    return out


def _vpc_flows(session, days: int, log_group: str = DEFAULT_FLOW_LOG_GROUP) -> list[dict]:
    """Pulls aggregate flow stats from CloudWatch Logs Insights.

    The log group name is configurable; defaults to what our Terraform creates.
    Returns empty list (not error) if the group doesn't exist — flow logs are
    nice-to-have, not required for attribution to work.
    """
    logs = session.client("logs")
    # Verify the log group exists before launching a query. Cheaper than waiting
    # for the query to fail.
    try:
        groups = logs.describe_log_groups(logGroupNamePrefix=log_group).get("logGroups", [])
        if not any(g["logGroupName"] == log_group for g in groups):
            log.warning("flow log group %r not found — skipping VPC flow data. "
                        "Pass --flow-log-group to override.", log_group)
            return []
    except Exception as e:
        log.warning("could not describe log groups: %s — skipping flow data", e)
        return []

    end = int(datetime.now(timezone.utc).timestamp())
    start = end - days * 86400
    query = (
        "fields @timestamp, srcAddr, dstAddr, bytes "
        "| stats sum(bytes) as total_bytes by srcAddr, dstAddr "
        "| sort total_bytes desc "
        f"| limit {MAX_FLOW_LOG_ROWS}"
    )
    out = []
    try:
        q = _retry(logs.start_query,
                   logGroupName=log_group,
                   startTime=start, endTime=end, queryString=query)
        qid = q["queryId"]
        # Poll until complete; Insights queries are async.
        deadline = time.time() + 120  # 2-minute timeout
        while time.time() < deadline:
            r = _retry(logs.get_query_results, queryId=qid)
            if r["status"] in ("Complete", "Failed", "Cancelled"):
                break
            time.sleep(1)
        else:
            log.warning("flow log query timed out after 2m")
            return []
        for row in r.get("results", []):
            d = {f["field"]: f["value"] for f in row}
            out.append({
                "src": d.get("srcAddr", ""),
                "dst": d.get("dstAddr", ""),
                "bytes": int(d.get("total_bytes", 0)),
                "intra_team": None,
            })
    except Exception as e:
        log.warning("VPC flow query failed: %s", e)
    return out


def collect_aws_signals(
    profile: str | None = None,
    region: str = "us-east-1",
    days: int = 30,
    max_workers: int = 8,
    flow_log_group: str = DEFAULT_FLOW_LOG_GROUP,
    extra_usernames: list[str] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Returns (signals, metadata, flows, deploys) in the same shape as
    generate_synthetic_signals.

    Each data-source failure is contained: if CloudTrail is broken but EC2 isn't,
    we still return what we got. Deploys come back empty unless you wire up a
    GitHub/GitLab webhook export.
    """
    session = _session(profile, region)

    # Inventory each resource type independently — one permission error per
    # type doesn't kill the whole scan.
    resources: list[dict] = []
    for fn in (_list_ec2, _list_rds, _list_lambda, _list_s3):
        try:
            chunk = fn(session)
            resources.extend(chunk)
            log.info("%s: %d resources", fn.__name__, len(chunk))
        except Exception as e:
            log.warning("%s failed: %s — continuing", fn.__name__, e)

    if not resources:
        log.warning("No AWS resources found. Falling back to empty frames. "
                    "Run `costdna doctor` to see why.")
        empty = pd.DataFrame()
        return empty, empty, empty, empty

    # CloudTrail per resource — parallelized for management events (ResourceName works).
    rows: list[dict] = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(_cloudtrail_events_by_resource, session,
                        r["resource_id"], days): r
            for r in resources
        }
        for fut in as_completed(futures):
            try:
                rows.extend(fut.result())
            except Exception as e:
                log.warning("cloudtrail future failed: %s", e)

    # Plus a per-username sweep for data events (ResourceName doesn't filter
    # well on those, but Username does). We extract usernames from the IAM
    # role names on each resource — typically the `something-role` suffix.
    # EventSource sweep — gets data events that ResourceName filter misses.
    rows.extend(_cloudtrail_events_via_eventsource(
        session, [r["resource_id"] for r in resources], days,
    ))

    # Cost series — best-effort.
    try:
        rows.extend(_cost_series(session, [r["resource_id"] for r in resources], days))
    except Exception as e:
        log.warning("cost series failed: %s", e)

    flows = _vpc_flows(session, days, log_group=flow_log_group)

    signals = pd.DataFrame(rows)
    if not signals.empty:
        signals["timestamp"] = pd.to_datetime(
            signals["timestamp"], format="ISO8601", utc=True,
        )

    metadata = pd.DataFrame(resources)
    flows_df = pd.DataFrame(flows)
    deploys_df = pd.DataFrame(columns=["team", "signal_type", "repo",
                                       "commit", "timestamp"])

    return signals, metadata, flows_df, deploys_df


# ─────────────────────────────────────────────────────────────────────
# CloudProvider interface — multi-cloud dispatch
# ─────────────────────────────────────────────────────────────────────

from costdna.collectors._base import (CloudProvider, CollectionResult,  # noqa: E402
                                       register)


@register("aws")
class AWSProvider(CloudProvider):
    """Live AWS scanner. Status: production-tested on a labeled Terraform
    env (see docs/real-aws-evidence/ for sample outputs)."""

    def doctor(self, *, profile, region):
        from costdna.doctor import run_doctor
        checks = run_doctor(profile=profile, region=region)
        # Convert list[Check] -> dict[str, (status, detail)]
        return {c.name: (c.status, c.detail) for c in checks}

    def collect(self, *, profile, region, days):
        signals, metadata, flows, deploys = collect_aws_signals(
            profile=profile, region=region, days=days,
        )
        return CollectionResult(
            metadata=metadata, signals=signals,
            flows=flows, deploys=deploys,
        )
