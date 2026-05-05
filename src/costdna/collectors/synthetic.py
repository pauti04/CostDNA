"""Synthetic signal generator with realistic hard cases.

Four teams, each with team-distinctive baseline behavior:
  backend  — steady weekday daytime activity, web-tier traffic, frequent deploys
  data     — overnight batch jobs, periodic spikes, long-running queries
  ml       — bursty training runs, large S3 reads, weekend usage
  platform — shared infra; touched by every team

On top of the clean per-team resources we inject four kinds of realistic noise.
This is what stops the model from scoring 100% — and what makes the project
interesting:

  shared_service  — primary team but heavy cross-team traffic (~30% of events
                    come from a different team)
  reassigned      — owned by team A in the first half of the window, team B
                    in the second half. Label = current owner (team B).
  sparse          — few events; cold-storage S3 buckets, infrequent Lambdas.
                    Hard to fingerprint with little data.
  cross_team      — used roughly equally by two teams. Label = the team whose
                    role created the resource (control plane wins).

Output schema matches collectors.aws so downstream code is source-agnostic.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from costdna import TEAMS

RESOURCE_TYPES = ("ec2", "rds", "lambda", "s3")


@dataclass(frozen=True)
class TeamProfile:
    name: str
    peak_hour: int
    weekend_ratio: float
    burst_factor: float
    n_users: int
    # IAM role names are *realistic* — the team isn't in the name. The model
    # has to infer team membership from behavior, not read it off the role.
    role_pool: tuple[str, ...]
    vpc_cidr: str
    cost_base: float


PROFILES = {
    # Each team has a weak naming hint that's realistic — they all share an
    # internal "tribe" name (apicore, etl, mlops, devops). Discovery should
    # find these, but they don't *guarantee* the team (e.g., a Lambda named
    # `apicore-callback` could be backend's primary OR a shared service).
    "backend": TeamProfile(
        "backend", 14, 0.05, 0.2, 8,
        role_pool=("apicore-execution-role", "apicore-ec2-web", "apicore-lambda-rest",
                   "apicore-rds-readonly", "apicore-s3-assets"),
        vpc_cidr="10.1.0.0/16", cost_base=0.5,
    ),
    "data": TeamProfile(
        "data", 2, 0.15, 0.6, 4,
        role_pool=("etl-runner-role", "etl-glue-execution", "etl-rds-warehouse",
                   "etl-lambda-batch", "etl-s3-datalake"),
        vpc_cidr="10.2.0.0/16", cost_base=0.8,
    ),
    "ml": TeamProfile(
        "ml", 22, 0.40, 1.4, 3,
        role_pool=("mlops-sagemaker-training", "mlops-ec2-gpu", "mlops-lambda-inference",
                   "mlops-s3-models", "mlops-rds-feature-store"),
        vpc_cidr="10.3.0.0/16", cost_base=1.5,
    ),
    "platform": TeamProfile(
        "platform", 12, 0.20, 0.3, 6,
        role_pool=("devops-eks-node", "devops-cw-writer", "devops-lambda-utils",
                   "devops-s3-logs", "devops-rds-tools"),
        vpc_cidr="10.0.0.0/16", cost_base=0.4,
    ),
}


def _role_for(team: str, rtype: str, rng: random.Random) -> str:
    """Pick a realistic IAM role for this resource. The role name doesn't
    contain the team — only the resource type prefix gives a weak hint."""
    pool = [r for r in PROFILES[team].role_pool if rtype in r] or list(PROFILES[team].role_pool)
    return rng.choice(pool)


_NAMING_PREFIXES = ("prod", "stg", "dev", "shared", "internal")


def _resource_id(rtype: str, kind: str, idx: int, rng: random.Random) -> str:
    """Realistic-looking resource ID. Doesn't encode team in the name."""
    prefix = rng.choice(_NAMING_PREFIXES)
    suffix = f"{rng.randrange(16**8):08x}"
    if rtype == "ec2":
        return f"i-{suffix}"
    if rtype == "rds":
        return f"{prefix}-rds-{suffix[:6]}"
    if rtype == "lambda":
        return f"{prefix}-fn-{suffix[:6]}"
    if rtype == "s3":
        return f"{prefix}-bucket-{suffix[:8]}"
    return f"{prefix}-{rtype}-{suffix[:6]}"


def _resource(team: str, rtype: str, idx: int, kind: str, rng: random.Random,
              reassigned_from: str | None = None) -> dict:
    profile = PROFILES[team]
    return {
        "resource_id": _resource_id(rtype, kind, idx, rng),
        "resource_type": rtype,
        "team": team,                       # ground truth label
        "kind": kind,                       # clean / shared_service / reassigned / sparse / cross_team
        "reassigned_from": reassigned_from, # only set for kind=reassigned
        "iam_role": _role_for(team, rtype, rng),
        "vpc_cidr": profile.vpc_cidr,
        "created_at": (datetime.now(timezone.utc)
                       - timedelta(days=rng.randint(30, 365))).isoformat(),
    }


def _unowned_resource(kind: str, rtype: str, idx: int, rng: random.Random) -> dict:
    """Resources with no team owner — the realistic 'mess' of a lived-in account.

    These get team='unowned' in metadata. They're excluded from training labels
    (no team to predict) but the model still runs inference on them. The anomaly
    detector catches them because they don't fit any team's behavioral centroid.
    """
    if kind == "vendor":
        # Looks like a vendor's forwarder/scanner — own IAM role, polling pattern.
        rid_choices = {
            "lambda": ["DatadogForwarder", "snyk-scanner-fn", "newrelic-cw-export"],
            "s3":     ["cloudflare-access-logs", "datadog-archive", "snyk-reports"],
            "ec2":    ["i-vendor-bastion"],
            "rds":    ["vendor-rum-store"],
        }
        rid = rng.choice(rid_choices.get(rtype, [f"vendor-{rtype}-{idx}"]))
        return {
            "resource_id": rid, "resource_type": rtype, "team": "unowned",
            "kind": "vendor", "reassigned_from": None,
            "iam_role": rng.choice(["DatadogIntegrationRole", "SnykScannerRole",
                                    "CloudflareLogsRole"]),
            "vpc_cidr": "",
            "created_at": (datetime.now(timezone.utc)
                           - timedelta(days=rng.randint(180, 800))).isoformat(),
        }

    if kind == "legacy":
        # Old naming convention from a previous architecture; sparse access.
        suffix = rng.choice(["2018", "2019", "2020"])
        rid_choices = {
            "lambda": [f"billing-export-{suffix}", f"old-cron-{suffix}"],
            "s3":     [f"old-billing-bucket-{suffix}", f"deprecated-archive-{suffix}"],
            "ec2":    [f"i-legacy-{suffix}"],
            "rds":    [f"legacy-warehouse-{suffix}"],
        }
        rid = rng.choice(rid_choices.get(rtype, [f"legacy-{rtype}-{suffix}"]))
        return {
            "resource_id": rid, "resource_type": rtype, "team": "unowned",
            "kind": "legacy", "reassigned_from": None,
            "iam_role": f"legacy-{suffix}-role",
            "vpc_cidr": "10.99.0.0/16",   # old VPC
            "created_at": (datetime.now(timezone.utc)
                           - timedelta(days=rng.randint(800, 2000))).isoformat(),
        }

    if kind == "orphan":
        # Created by an ex-employee — IAM principal no longer resolves.
        former_user = rng.choice(["alice.smith", "bob-2019", "former-contractor",
                                  "intern-summer-2020"])
        rid_choices = {
            "lambda": [f"{former_user}-test-fn"],
            "s3":     [f"{former_user}-personal-bucket"],
            "ec2":    [f"i-{former_user.replace('.', '')[:8]}"],
            "rds":    [f"{former_user}-sandbox-db"],
        }
        rid = rng.choice(rid_choices.get(rtype, [f"orphan-{rtype}-{idx}"]))
        return {
            "resource_id": rid, "resource_type": rtype, "team": "unowned",
            "kind": "orphan", "reassigned_from": None,
            "iam_role": f"deleted-user-{former_user}",
            "vpc_cidr": "",
            "created_at": (datetime.now(timezone.utc)
                           - timedelta(days=rng.randint(400, 1500))).isoformat(),
        }

    if kind == "shadow":
        # Console-deployed, no IaC — random/default names.
        rid_choices = {
            "lambda": ["myFunction-2", "untitled_function", "test-deploy-v3",
                       "Function-1234"],
            "s3":     ["my-test-bucket-7843", "tmp-uploads-staging",
                       "experiment-bucket-x"],
            "ec2":    ["i-shadow01", "i-consoletest"],
            "rds":    ["db-instance-1", "test-staging"],
        }
        rid = rng.choice(rid_choices.get(rtype, [f"shadow-{rtype}-{idx}"]))
        return {
            "resource_id": rid, "resource_type": rtype, "team": "unowned",
            "kind": "shadow", "reassigned_from": None,
            "iam_role": "lambda_basic_execution",  # AWS console default
            "vpc_cidr": "",
            "created_at": (datetime.now(timezone.utc)
                           - timedelta(days=rng.randint(7, 90))).isoformat(),
        }

    raise ValueError(f"unknown unowned kind: {kind}")


def _resources(rng: random.Random, n_clean_per_type: int) -> list[dict]:
    out: list[dict] = []
    # Clean per-team resources (the easy cases).
    for team in TEAMS:
        for rtype in RESOURCE_TYPES:
            for i in range(n_clean_per_type):
                out.append(_resource(team, rtype, i, "clean", rng))

    # Hard cases — small absolute counts but they tank accuracy if the model
    # only memorizes IAM-role prefixes.
    non_platform = [t for t in TEAMS if t != "platform"]

    # 1. Shared services: backend's primary, but data + ml hit it a lot.
    for i, rtype in enumerate(("rds", "s3", "lambda")):
        out.append(_resource("backend", rtype, i, "shared_service", rng))

    # 2. Reassigned: was data's, now ml owns it (e.g. ML team took over a feature store).
    out.append(_resource("ml", "rds", 0, "reassigned", rng, reassigned_from="data"))
    out.append(_resource("ml", "s3", 0, "reassigned", rng, reassigned_from="data"))
    out.append(_resource("backend", "lambda", 0, "reassigned", rng, reassigned_from="platform"))

    # 3. Sparse: very few events. Cold-storage S3, rarely-invoked Lambdas.
    for i, team in enumerate(rng.sample(non_platform, 2)):
        out.append(_resource(team, "s3", i, "sparse", rng))
    out.append(_resource("ml", "lambda", 0, "sparse", rng))

    # 4. Cross-team: used roughly equally by two teams.
    for i in range(3):
        primary = rng.choice(non_platform)
        out.append(_resource(primary, "ec2", i, "cross_team", rng))

    # 5. Unowned: the realistic mess. These don't belong to any team.
    # The model should give them low confidence; the anomaly detector should
    # flag them. They're excluded from labeled training data.
    out.append(_unowned_resource("vendor", "lambda", 0, rng))
    out.append(_unowned_resource("vendor", "s3", 0, rng))
    out.append(_unowned_resource("legacy", "s3", 0, rng))
    out.append(_unowned_resource("legacy", "lambda", 0, rng))
    out.append(_unowned_resource("orphan", "ec2", 0, rng))
    out.append(_unowned_resource("orphan", "lambda", 0, rng))
    out.append(_unowned_resource("shadow", "lambda", 0, rng))
    out.append(_unowned_resource("shadow", "lambda", 1, rng))

    return out


def _events_for_unowned(r: dict, days: int, rng: random.Random) -> list[dict]:
    """Distinct event patterns for unowned-mess resources. Each kind has a
    behavioral signature the anomaly detector should pick up."""
    events = []
    now = datetime.now(timezone.utc)

    if r["kind"] == "vendor":
        # Polling at a fixed cadence — every hour exactly.
        for h in range(days * 24):
            ts = now - timedelta(hours=h)
            events.append({
                "resource_id": r["resource_id"],
                "resource_type": r["resource_type"],
                "signal_type": "cloudtrail_event",
                "user_identity": r["iam_role"],
                "iam_role": r["iam_role"],
                "event_name": rng.choice(["GetObject", "PutObject", "Invoke"]),
                "source_account": "999999999999",  # external account
                "value": 1,
                "timestamp": ts.replace(minute=0, second=rng.randint(0, 5)).isoformat(),
            })
        return events

    if r["kind"] == "legacy":
        # Sparse cron access — once a day at 2am.
        for d in range(days):
            if rng.random() < 0.3:  # not even every day
                ts = (now - timedelta(days=d)).replace(hour=2,
                                                       minute=rng.randint(0, 59))
                events.append({
                    "resource_id": r["resource_id"],
                    "resource_type": r["resource_type"],
                    "signal_type": "cloudtrail_event",
                    "user_identity": r["iam_role"],
                    "iam_role": r["iam_role"],
                    "event_name": "ListObjects",
                    "source_account": "111111111111",
                    "value": 1,
                    "timestamp": ts.isoformat(),
                })
        return events

    if r["kind"] == "orphan":
        # Near-zero activity — maybe 1-3 events total over the window.
        for _ in range(rng.randint(0, 3)):
            ts = now - timedelta(hours=rng.uniform(0, days * 24))
            events.append({
                "resource_id": r["resource_id"],
                "resource_type": r["resource_type"],
                "signal_type": "cloudtrail_event",
                "user_identity": "AWSReservedSSO_AdministratorAccess",
                "iam_role": r["iam_role"],
                "event_name": "Describe",
                "source_account": "111111111111",
                "value": 1,
                "timestamp": ts.isoformat(),
            })
        return events

    if r["kind"] == "shadow":
        # Sporadic, manual — bursts of 5-20 events, then nothing for days.
        n_bursts = rng.randint(1, 3)
        for _ in range(n_bursts):
            burst_day = rng.randint(0, days - 1)
            burst_size = rng.randint(5, 20)
            for _ in range(burst_size):
                ts = (now - timedelta(days=burst_day)).replace(
                    hour=rng.randint(9, 22), minute=rng.randint(0, 59))
                events.append({
                    "resource_id": r["resource_id"],
                    "resource_type": r["resource_type"],
                    "signal_type": "cloudtrail_event",
                    "user_identity": "AWSReservedSSO_PowerUser",  # console user
                    "iam_role": r["iam_role"],
                    "event_name": rng.choice(["Invoke", "UpdateFunctionCode",
                                              "CreateFunction"]),
                    "source_account": "111111111111",
                    "value": 1,
                    "timestamp": ts.isoformat(),
                })
        return events

    return []


def _events_for_resource(r: dict, days: int, rng: random.Random) -> list[dict]:
    """One CloudTrail-style row per API call. Activity follows team profile,
    modulated by the resource's `kind` (sparse → fewer, shared_service → mixed,
    unowned kinds → distinct anomalous patterns)."""
    if r["team"] == "unowned":
        return _events_for_unowned(r, days, rng)

    profile = PROFILES[r["team"]]
    events = []
    now = datetime.now(timezone.utc)

    base_calls_per_day = rng.randint(40, 200)
    if r["kind"] == "sparse":
        base_calls_per_day = rng.randint(2, 8)

    for day_offset in range(days):
        day = now - timedelta(days=day_offset)
        is_weekend = day.weekday() >= 5

        # Reassigned: first half of window uses old team's profile, second half new.
        if r["kind"] == "reassigned" and day_offset >= days // 2:
            active_team = r["reassigned_from"]
        else:
            active_team = r["team"]
        active_profile = PROFILES[active_team]

        if is_weekend:
            n_calls = int(base_calls_per_day * active_profile.weekend_ratio * 2)
        else:
            n_calls = int(base_calls_per_day * (1 - active_profile.weekend_ratio))

        for _ in range(n_calls):
            # Most events come from the resource's primary team, but some kinds
            # mix in cross-team callers. The 60-70% noise is what makes these
            # genuinely hard — at lower noise the primary-team signal still
            # dominates and a logistic regression solves the problem.
            caller_team = active_team
            if r["kind"] == "shared_service" and rng.random() < 0.65:
                caller_team = rng.choice([t for t in TEAMS if t != active_team])
            elif r["kind"] == "cross_team" and rng.random() < 0.70:
                caller_team = rng.choice([t for t in TEAMS if t != active_team])
            elif r["team"] == "platform" and rng.random() < 0.65:
                caller_team = rng.choice([t for t in TEAMS if t != "platform"])

            caller_profile = PROFILES[caller_team]
            hour = int(np.clip(rng.gauss(caller_profile.peak_hour, 3), 0, 23))
            ts = day.replace(hour=hour,
                             minute=rng.randint(0, 59),
                             second=rng.randint(0, 59))
            caller_role = _role_for(caller_team, r["resource_type"], rng)
            user = f"{caller_role}-user{rng.randint(0, caller_profile.n_users - 1)}"
            events.append({
                "resource_id": r["resource_id"],
                "resource_type": r["resource_type"],
                "signal_type": "cloudtrail_event",
                "user_identity": user,
                "iam_role": caller_role,
                "event_name": rng.choice(["GetObject", "Invoke", "DescribeInstances",
                                          "PutItem", "Query", "RunInstances"]),
                "source_account": "111111111111",
                "value": 1,
                "timestamp": ts.isoformat(),
            })
    return events


def _flows(resources: list[dict], rng: random.Random) -> list[dict]:
    """VPC flow log rows. Same-team resources talk a lot; shared-services and
    cross-team resources have substantial inter-team flows."""
    flows = []
    by_team: dict[str, list[dict]] = {}
    for r in resources:
        by_team.setdefault(r["team"], []).append(r)

    for team, members in by_team.items():
        for src in members:
            partners = rng.sample(members, k=min(len(members), rng.randint(2, 5)))
            for dst in partners:
                if src["resource_id"] == dst["resource_id"]:
                    continue
                flows.append({
                    "src": src["resource_id"], "dst": dst["resource_id"],
                    "bytes": rng.randint(10_000, 10_000_000), "intra_team": True,
                })

    teams_list = list(by_team.keys())

    # Sparse cross-team chatter for the clean resources.
    for _ in range(len(resources) // 4):
        t1, t2 = rng.sample(teams_list, 2)
        src = rng.choice(by_team[t1])
        dst = rng.choice(by_team[t2])
        flows.append({"src": src["resource_id"], "dst": dst["resource_id"],
                      "bytes": rng.randint(1_000, 100_000), "intra_team": False})

    # Heavy cross-team flows for the noisy kinds — this is the structural noise
    # that makes the problem hard.
    for r in resources:
        if r["kind"] not in ("shared_service", "cross_team"):
            continue
        for other_team in teams_list:
            if other_team == r["team"]:
                continue
            for partner in rng.sample(by_team[other_team],
                                      k=min(2, len(by_team[other_team]))):
                flows.append({"src": partner["resource_id"], "dst": r["resource_id"],
                              "bytes": rng.randint(100_000, 5_000_000),
                              "intra_team": False})
    return flows


def _cost_series(resources: list[dict], events: list[dict], deploys: list[dict],
                 days: int, rng: random.Random) -> list[dict]:
    """Hourly cost driven by *actual event distribution* per resource.

    A shared-services resource that gets traffic from three teams across the
    day will show cost peaks at three different hours — and that's exactly
    what makes its team-attribution hard. Hard-coding cost shape to the
    primary team would leak the answer.

    Deploys still inject a 1-3h-lagged causal spike the explainer recovers.
    """
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    hours = days * 24

    # Bucket events by (resource_id, hour offset).
    event_hist: dict[tuple[str, int], int] = {}
    for ev in events:
        ts = datetime.fromisoformat(ev["timestamp"])
        h_offset = int((now - ts).total_seconds() // 3600)
        if 0 <= h_offset < hours:
            key = (ev["resource_id"], h_offset)
            event_hist[key] = event_hist.get(key, 0) + 1

    deploy_index: dict[tuple[str, int], list[dict]] = {}
    for d in deploys:
        ts = datetime.fromisoformat(d["timestamp"])
        h_offset = int((now - ts).total_seconds() // 3600)
        deploy_index.setdefault((d["team"], h_offset), []).append(d)

    rows = []
    for r in resources:
        # Unowned resources use a generic baseline; no team profile.
        if r["team"] == "unowned":
            profile = PROFILES["platform"]   # reasonable baseline
        else:
            profile = PROFILES[r["team"]]
        # Cost-per-event reflects the resource's actual workload class, not its
        # team — an ml-team RDS still costs RDS-like money, not ML-like money.
        cost_per_event = {"ec2": 0.05, "rds": 0.08, "lambda": 0.001, "s3": 0.0005}[r["resource_type"]]
        idle_cost = profile.cost_base * 0.3 * rng.uniform(0.7, 1.3)
        if r["kind"] in ("sparse", "orphan", "legacy"):
            idle_cost *= 0.05    # cheap to keep around, hardly used

        for h in range(hours):
            ts = now - timedelta(hours=h)
            n_events = event_hist.get((r["resource_id"], h), 0)
            usage_cost = n_events * cost_per_event * rng.uniform(0.8, 1.2)
            deploy_spike = 0.0
            for lag in (1, 2, 3):
                if (r["team"], h + lag) in deploy_index:
                    n_dep = len(deploy_index[(r["team"], h + lag)])
                    deploy_spike += n_dep * profile.burst_factor * 1.5
            cost = idle_cost + usage_cost + deploy_spike * profile.cost_base
            rows.append({"resource_id": r["resource_id"], "signal_type": "cost",
                         "value": round(cost, 4), "timestamp": ts.isoformat()})
    return rows


def _deploys(rng: random.Random, days: int) -> list[dict]:
    rows = []
    now = datetime.now(timezone.utc)
    rates = {"backend": 5.0, "data": 1.5, "ml": 0.8, "platform": 0.3}
    for team, rate in rates.items():
        for _ in range(int(rate * days)):
            ts = now - timedelta(hours=rng.uniform(0, days * 24))
            rows.append({"team": team, "signal_type": "deploy",
                         "repo": f"{team}-{rng.choice(['api', 'pipeline', 'training', 'svc'])}",
                         "commit": f"{rng.randrange(16**7):07x}",
                         "timestamp": ts.isoformat()})
    return rows


def generate_synthetic_signals(
    n_per_type_per_team: int = 3,
    days: int = 14,
    seed: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Returns (signals, metadata, flows, deploys).

    Metadata includes a `kind` column distinguishing clean resources from the
    four hard-case categories — useful for per-kind accuracy analysis.
    """
    rng = random.Random(seed)
    np.random.seed(seed)

    resources = _resources(rng, n_per_type_per_team)

    cloudtrail = []
    for r in resources:
        cloudtrail.extend(_events_for_resource(r, days, rng))

    deploys = _deploys(rng, days)
    cost = _cost_series(resources, cloudtrail, deploys, days, rng)
    flows = _flows(resources, rng)

    signals = pd.DataFrame(cloudtrail + cost)
    signals["timestamp"] = pd.to_datetime(signals["timestamp"], format="ISO8601", utc=True)

    metadata = pd.DataFrame(resources)
    flows_df = pd.DataFrame(flows)
    deploys_df = pd.DataFrame(deploys)
    deploys_df["timestamp"] = pd.to_datetime(deploys_df["timestamp"], format="ISO8601", utc=True)

    return signals, metadata, flows_df, deploys_df
