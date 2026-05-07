# Running CostDNA against a real AWS account

A 1-day plan: `terraform apply` in the morning, `costdna scan` against real AWS data by evening. Total active time ~3 hours, total wall-clock ~12 hours.

> **TL;DR — the two-command path:**
> ```bash
> bash scripts/real-aws-test.sh    # day 0: stand up env + start simulator on EC2
> # ...wait 2-7 days for CloudTrail signal to accumulate...
> bash scripts/real-aws-finish.sh  # day N: scan, save, terraform destroy
> ```
> The wrappers handle preflight, $50 budget alarm, terraform, IAM permissions, the 24/7 EC2 simulator, and teardown. The hour-by-hour walkthrough below explains what's happening under the hood — read it once if you want to know what each step does, or skip straight to the wrappers.

## Prerequisites

- AWS account (free tier is fine — total spend ~$3-10 for the demo)
- AWS CLI installed and `aws configure` done with admin or near-admin permissions
- Terraform ≥ 1.5
- Python 3.10+
- `pip install -e .` from the CostDNA repo

The admin permissions matter: the simulators need `sts:AssumeRole` into team IAM roles. A user with read-only AWS access cannot run this end-to-end.

## What you'll spend

| Resource | Daily cost |
|---|---|
| 8× t3.micro EC2 (free tier) | ~$0 |
| 4× db.t3.micro RDS | ~$0.30 |
| Lambda + S3 | ~$0.05 |
| **CloudTrail data events** (the critical bit) | ~$0.10 per 100K events |
| VPC Flow Logs to CloudWatch | ~$0.50 |
| **Total** | **~$2-5/day** |

Tear down with `terraform destroy` when done.

## Hour-by-hour walkthrough

### Hour 0 — Apply Terraform (15 min)

```bash
cd terraform
terraform init
terraform apply
```

Expected: 4 VPCs, 8 EC2, 4 RDS, 4 Lambda, 4 S3 buckets, 4 IAM roles (one per team), 4 unowned-mess resources, CloudTrail trail with **data events enabled**, VPC Flow Logs at `/aws/vpc/flowlogs`. The `labels.csv` file appears in the repo root.

If `terraform apply` errors:
- **`InvalidParameterValue: Engine version 15.5 not supported`** — postgres version moves. Run `aws rds describe-db-engine-versions --engine postgres --query 'DBEngineVersions[0].EngineVersion' --output text` and put that version in `terraform/teams.tf`.
- **`SubnetGroupDoesNotMeetRequirements`** — your region only has one AZ. Pick a different region in `terraform/variables.tf`.

### Hour 0:15 — Preflight (5 min)

```bash
costdna doctor --aws-profile YOURS
```

Expected: 5 ✓ checks. If any are ✗, the message tells you what to fix.

### Hour 0:20 — Launch the simulators (5 min setup, runs all day)

Open 4 terminal tabs, one per team. The sleep values stagger them so they don't overwhelm AWS rate limits:

```bash
# Terminal 1
while true; do python -m simulation.backend_workload; sleep 60; done

# Terminal 2
while true; do python -m simulation.data_workload; sleep 90; done

# Terminal 3
while true; do python -m simulation.ml_workload; sleep 120; done

# Terminal 4
while true; do python -m simulation.platform_workload; sleep 180; done
```

Each loop assumes the team's IAM role *for that team's calls only*, so CloudTrail attributes events correctly. Without the AssumeRole step, every event would look like your user and behavioral attribution would be impossible.

**Leave running for 8-12 hours.** During that time:
- CloudTrail accumulates ~5K-30K events per resource
- VPC Flow Logs accumulate flows between team resources
- Cost Explorer accumulates hourly cost data

### Hour 12 — Stop simulators, scan (5 min)

```bash
# Stop the loops (Ctrl+C in each terminal), wait ~10 min for CloudTrail to flush.

costdna scan --aws-profile YOURS --days 1 --save-dir runs/real-1
```

Expected output: an executive summary, model accuracy panel, attribution table, anomaly list, and cost-spike explanations — all driven by real AWS data.

### Hour 12:30 — Optionally apply tags

Inspect first:
```bash
costdna apply --predictions runs/real-1/predictions.csv  # dry-run
```

If satisfied, write tags:
```bash
costdna apply --predictions runs/real-1/predictions.csv --apply --aws-profile YOURS
```

### Hour 12:35 — Tear down

```bash
cd terraform && terraform destroy
```

Total spend: usually $3-8.

## What about a 5-day run?

For more rigorous numbers (real weekend/weekday differentiation, longer cost time-series for `cost_slope`/`cost_variance`/`cost_autocorr` features), let it run for 5 days. Same setup, just leave the simulators going. Cost ~$15-30.

## Caveats for the 1-day run

| Feature | 1-day quality | 5-day quality |
|---|---|---|
| `event_count`, `unique_users`, `unique_roles`, `peak_hour`, `cross_account` | ✓ Strong | ✓ Strong |
| `weekend_ratio` | ✗ Meaningless (all one day) | ✓ Strong |
| `cost_slope`, `cost_variance`, `cost_autocorr` | ⚠ Partial — Cost Explorer has ~24h ingestion delay | ✓ Strong |
| Anomaly detection | ✓ Strong | ✓ Strong |
| Drift detection | ✗ Need 2 runs | ✓ Strong |

## Validating on real cloud data without your own AWS account

The strongest non-AWS validation is Microsoft's **Azure Public Dataset V2** —
2.6 million anonymized VMs across thousands of subscriptions, with real
behavioral patterns. Used in 100+ academic papers. Free.

### Download

```bash
mkdir -p data
curl -L -o data/vmtable.csv.gz \
  https://azurepublicdatasettraces.blob.core.windows.net/azurepublicdatasetv2/trace_data/vmtable/vmtable.csv.gz
```

The file is ~417MB compressed (~2GB uncompressed). Download takes 5-10 minutes.
For the latest URL, see [AzurePublicDatasetLinksV2.txt](https://github.com/Azure/AzurePublicDataset/blob/master/AzurePublicDatasetLinksV2.txt).

### Run

```bash
costdna scan --azure-trace data/vmtable.csv.gz --epochs 200
costdna benchmark --azure-trace data/vmtable.csv.gz --kfold 5
```

The loader auto-samples the top 10 subscriptions (your "teams") with up to 200
VMs each, builds graph edges from `deployment_id` (analogous to AWS VPCs), and
synthesizes hourly cost-proxy readings from the per-VM CPU summary stats.

### What gets validated

- Behavioral feature extraction (peak hour, weekend ratio, cost-shape autocorr)
- Graph-based label propagation
- GraphSAGE attribution
- Anomaly detection via centroid distance
- Active learning loop

### Limitation

The vmtable contains *summary* CPU stats (max, avg, p95) rather than the full
hourly time-series (which is 140GB across 195 files). The behavioral curves we
generate are reconstructed from the summary stats with realistic daily/weekly
modulation per VM category. The team labels (subscription_id) and graph
structure (deployment_id) are 100% real; the time-series is approximated.

For a stricter test, download one or more `vm_cpu_readings-file-NNN-of-195.csv.gz`
files (each ~700MB) and we can extend the loader to use real hourly data.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `costdna scan` returns 0 events | Simulators not running, or AssumeRole failed | Check logs in each simulator terminal; ensure your AWS profile has `sts:AssumeRole` |
| All confidence scores < 0.5 | Not enough behavioral data | Run simulators for longer (4+ hours minimum) |
| `costdna doctor` says "Cost Explorer not enabled" | First-time accounts | Enable in Console → Billing → Cost Explorer; ~24h to populate |
| `AccessDenied` on AssumeRole | Trust policy not applied | Re-run `terraform apply`; verify with `aws iam get-role --role-name backend-svc-role` |
| All resources predicted as one team | Model collapsed | More diverse seed labels via `costdna learn` |
| Bill higher than expected | CloudTrail data events on production-scale traffic | The data events filter in `terraform/main.tf` only enables S3+Lambda — should be cheap |
