"""Generate a sample AWS Cost & Usage Report CSV for the /your-account demo.

Visitors who don't have a real CUR can click "Try with sample data" and load
this file. The data is plausible — multi-team account, mix of services, ~50%
tag completeness, a handful of unattributed resources for the demo to find.

Output: web/public/sample-cur.csv (~50KB; safe to ship).

Reproduce: PYTHONPATH=src python scripts/gen-sample-cur.py
"""
from __future__ import annotations

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "web" / "public" / "sample-cur.csv"

# Standard CUR columns the lightweight analyzer in web/src/lib/cur-analyze.ts
# looks for. Real CURs have ~150 columns; we ship only the ones the analyzer
# actually consumes, plus a few obviously-useful ones for human readers.
COLUMNS = [
    "lineItem/UsageAccountId",
    "lineItem/UsageStartDate",
    "lineItem/UsageEndDate",
    "lineItem/ProductCode",
    "lineItem/ResourceId",
    "lineItem/UnblendedCost",
    "lineItem/UsageType",
    "lineItem/Operation",
    "resourceTags/user:team",
    "resourceTags/user:environment",
]

ACCOUNT = "111122223333"

# Realistic team distribution. Some resources tagged with team, some not.
# The unattributed-without-tag ones are what the analyzer's heuristic
# pattern-matching should partially recover; some genuinely have no signal.
TEAMS = [
    ("backend", "prod"),
    ("backend", "stg"),
    ("data", "prod"),
    ("ml", "prod"),
    ("ml", "stg"),
    ("platform", "prod"),
]

# Resource templates: (name_pattern, product, typical_monthly_cost, has_tag_prob)
# Names follow the conventions costdna's pattern-matcher recognizes:
#   apicore-* → backend
#   etl-*     → data
#   mlops-*   → ml
#   devops-*  → platform
RESOURCE_TEMPLATES = [
    ("apicore-api-{idx:03d}",  "AmazonEC2",   85.0,  ("backend", "prod"), 0.9),
    ("apicore-db-{idx:03d}",   "AmazonRDS",   180.0, ("backend", "prod"), 0.9),
    ("apicore-edge-{idx:03d}", "AmazonCloudFront", 25.0, ("backend", "prod"), 0.8),
    ("etl-batch-{idx:03d}",    "AmazonEC2",   140.0, ("data", "prod"),    0.7),
    ("etl-warehouse-{idx:03d}","AmazonRedshift", 320.0, ("data", "prod"), 0.95),
    ("etl-pipeline-{idx:03d}", "AWSGlue",     65.0,  ("data", "prod"),    0.6),
    ("mlops-train-{idx:03d}",  "AmazonEC2",   240.0, ("ml", "prod"),      0.85),
    ("mlops-infer-{idx:03d}",  "AWSLambda",   35.0,  ("ml", "prod"),      0.7),
    ("mlops-fs-{idx:03d}",     "AmazonS3",    18.0,  ("ml", "stg"),       0.4),
    ("devops-eks-{idx:03d}",   "AmazonEKS",   95.0,  ("platform", "prod"), 0.9),
    ("devops-logs-{idx:03d}",  "AmazonCloudWatch", 22.0, ("platform", "prod"), 0.5),
    # Plausibly-untagged: vendor-owned + legacy resources
    ("dd-agent-{idx:03d}",     "AmazonEC2",   45.0,  None, 0.0),                    # Datadog agent — no team tag
    ("legacy-srv-{idx:03d}",   "AmazonEC2",   30.0,  None, 0.0),                    # Forgotten legacy
    ("orphan-bucket-{idx:03d}","AmazonS3",    8.0,   None, 0.0),                    # Orphan S3
]

USAGE_TYPES = {
    "AmazonEC2":        "BoxUsage:t3.medium",
    "AmazonRDS":        "InstanceUsage:db.t3.large",
    "AmazonRedshift":   "Node:dc2.large",
    "AmazonCloudFront": "DataTransfer-Out-Bytes",
    "AWSGlue":          "DPU-Hour:JobRun",
    "AWSLambda":        "Lambda-GB-Second",
    "AmazonS3":         "TimedStorage-ByteHrs",
    "AmazonEKS":        "AmazonEKS-Hours:cluster",
    "AmazonCloudWatch": "PutLogEvents",
}


def _resource_id(template: str, idx: int, product: str) -> str:
    base = template.format(idx=idx)
    # CUR resource_ids are usually ARN-shaped. We use the AWS conventional
    # short form to make the demo readable; the analyzer's name-pattern
    # heuristic operates on the short name regardless.
    if product == "AmazonEC2":
        return f"i-{abs(hash(base)) & 0xffffffff:08x}"
    if product == "AmazonRDS":
        return base
    if product == "AmazonS3":
        return base
    if product == "AWSLambda":
        return base
    if product == "AmazonRedshift":
        return f"redshift-cluster-{abs(hash(base)) & 0xffff:04x}"
    if product == "AWSGlue":
        return base
    if product == "AmazonEKS":
        return f"arn:aws:eks:us-east-1:{ACCOUNT}:cluster/{base}"
    if product == "AmazonCloudFront":
        return f"E{abs(hash(base)) & 0xffffffff:013X}"[:14]
    if product == "AmazonCloudWatch":
        return f"log-group-{base}"
    return base


def main():
    rng = random.Random(1337)
    rows = []
    start = datetime(2026, 5, 1)
    end = datetime(2026, 5, 31, 23, 59)

    # Emit one row per resource × per ~5 sample days in the billing window.
    # Real CURs are hourly, but for the demo a daily roll-up keeps the file
    # tiny while still demonstrating multi-team / multi-service shape.
    sample_days = [start + timedelta(days=d) for d in range(0, 31, 6)]

    for template, product, monthly, team_env, tag_prob in RESOURCE_TEMPLATES:
        # Number of resources of this kind (2-4 each, varied for realism).
        n_inst = rng.randint(2, 5)
        for i in range(n_inst):
            rid = _resource_id(template, i, product)
            tag_value = ""
            env_value = ""
            if team_env is not None and rng.random() < tag_prob:
                tag_value = team_env[0]
                env_value = team_env[1]
            # Spread the cost across sample days with some noise.
            daily = (monthly / 31) * (len(sample_days) / 5)  # rough scaling
            for d in sample_days:
                cost = round(daily * rng.uniform(0.7, 1.3), 4)
                if cost <= 0:
                    continue
                rows.append({
                    "lineItem/UsageAccountId": ACCOUNT,
                    "lineItem/UsageStartDate": d.isoformat(),
                    "lineItem/UsageEndDate": (d + timedelta(days=1)).isoformat(),
                    "lineItem/ProductCode": product,
                    "lineItem/ResourceId": rid,
                    "lineItem/UnblendedCost": f"{cost:.6f}",
                    "lineItem/UsageType": USAGE_TYPES.get(product, "Usage"),
                    "lineItem/Operation": "RunInstances" if product == "AmazonEC2" else "",
                    "resourceTags/user:team": tag_value,
                    "resourceTags/user:environment": env_value,
                })

    # Add a handful of data-transfer / cross-account lines with no resource_id
    # — typical of CURs and lets the demo show the "non-resource line items"
    # case the analyzer needs to handle gracefully.
    for d in sample_days:
        rows.append({
            "lineItem/UsageAccountId": ACCOUNT,
            "lineItem/UsageStartDate": d.isoformat(),
            "lineItem/UsageEndDate": (d + timedelta(days=1)).isoformat(),
            "lineItem/ProductCode": "AWSDataTransfer",
            "lineItem/ResourceId": "",
            "lineItem/UnblendedCost": f"{rng.uniform(2, 12):.6f}",
            "lineItem/UsageType": "DataTransfer-Regional-Bytes",
            "lineItem/Operation": "",
            "resourceTags/user:team": "",
            "resourceTags/user:environment": "",
        })

    rng.shuffle(rows)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    total = sum(float(r["lineItem/UnblendedCost"]) for r in rows)
    print(f"Wrote {OUT.relative_to(ROOT)}")
    print(f"  rows: {len(rows)}")
    print(f"  total spend: ${total:,.2f}")
    print(f"  file size: {OUT.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
