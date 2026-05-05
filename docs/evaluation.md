# CostDNA — evaluation guide

*One-pager you can forward to a teammate or manager who's deciding whether to let you run CostDNA against your AWS account. Plain English, no marketing.*

---

## What it does

CostDNA infers which team owns each AWS resource, by looking at how the resource is used — IAM principals, CloudTrail event patterns, VPC flow patterns, deploy timing, cost time-series shape. It outputs a CSV: resource ID → predicted team → confidence score → optional per-prediction explanation.

You then either review the predictions (low confidence ones) or apply them as AWS tags. After that, your existing FinOps dashboard (CloudHealth, Vantage, Apptio, Cost Explorer, Kubecost) can attribute previously-untagged spend.

## What it is *not*

- Not a dashboard. It's an input layer for the dashboard you already use.
- Not k8s-only. Works on any AWS resource that emits CloudTrail.
- Not magic. Confidence scores are calibrated (ECE = 0.001 in our tests), so when it says 0.6 it's right 60% of the time. You decide which threshold to trust.
- Not making API calls outside read-only AWS — no third-party SaaS, no data leaves your account during the scan.

## How a single evaluation runs

| Step | Time | Action |
|---|---|---|
| 1 | 5 min | We grant a read-only IAM role to CostDNA (policy below). |
| 2 | 10-15 min | The scan runs: pulls CloudTrail Lookup events, Cost Explorer aggregates, IAM role list, resource metadata. |
| 3 | <1 min | The model runs locally on the engineer's laptop — no data leaves the AWS account perimeter the engineer accesses. |
| 4 | — | Output: `predictions.csv` + an executive summary panel showing $-untagged → $-newly-attributable. |
| 5 | — | If we're applying tags: `costdna apply --dry-run` shows what tags would be written; `--apply` actually writes them. Both are auditable in CloudTrail. |

Total wall-clock: under an hour for accounts up to ~500 resources. Up to a few hours for larger accounts (mostly CloudTrail throttling).

## What permissions CostDNA needs

Read-only. Nothing more. Here's the exact IAM policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "cloudtrail:LookupEvents",
      "ce:GetCostAndUsage",
      "ce:GetCostAndUsageWithResources",
      "ec2:Describe*",
      "rds:Describe*",
      "lambda:List*",
      "lambda:Get*",
      "s3:ListAllMyBuckets",
      "s3:GetBucketLocation",
      "s3:GetBucketTagging",
      "iam:ListRoles",
      "iam:ListUsers",
      "iam:ListPolicies",
      "iam:GetRole",
      "logs:DescribeLogGroups",
      "logs:GetLogEvents",
      "ec2:DescribeFlowLogs"
    ],
    "Resource": "*"
  }]
}
```

If you need it scoped tighter (specific resource ARNs only), say so — we can scope to a list.

If you only want to grant `cloudtrail:LookupEvents` + `ce:GetCostAndUsage` to start, the model will run with reduced signal but still produce output. The other permissions are for completeness.

## What's the failure mode

**If predictions are wrong and we apply tags**: the only thing that happens is your AWS resources get tags they didn't have before, which can be reverted by writing a different tag. No service is affected; no traffic is rerouted; no IAM is changed. The dry-run mode (`--dry-run`) prints the exact tag-writes without making them, so you can audit before any state change.

**If the scan throttles CloudTrail**: it's adaptive — backs off automatically. Worst case: the scan takes longer.

**If we run out of Cost Explorer API budget**: scan still runs, just without the cost-time-series features. You get team predictions but not the spike-attribution features.

**If we don't have enough CloudTrail history (less than 24h)**: model accuracy drops. CostDNA was tested on 7-day windows. Anything less than 3 days will produce noisy results.

## What we'd report back to you

After the run, here's what you'd get in writing (anonymized to whatever level you want):

1. Summary numbers: total resources scanned, % that already had tags, % that CostDNA could attribute at ≥70% confidence, total $ involved.
2. The honest-failure cases: resources where CostDNA returned low confidence — usually shared-services or vendor infra. These are the resources that will benefit most from a tagging conversation with the responsible team.
3. Anomalies: resources that don't fit any team well (vendor infra, leaked-credential workloads, deprecated systems).
4. Optional: the explained-spike report, if there's a recent cost spike worth investigating.

Anonymization: resource IDs become `<resource-1>`, `<resource-2>`, etc. Team names stay (or get aliased if you prefer). $ amounts can be exact or rounded to nearest $100. Your call.

## What we'd ask in return

Permission to publish a sanitized writeup of the findings on the project's GitHub README and (eventually) a blog post. The writeup would say "an AWS account with N resources and ~$M monthly spend" — no company name, no specific resource IDs, no team names beyond "team-A / team-B / team-C". You get to review and approve before anything is published.

If you'd rather we publish nothing, that's fine too — we still get the satisfying engineering exercise of running it on real data, and you get the predictions to do whatever you want with.

## Getting started

1. Create an IAM user (or role, if you prefer cross-account `sts:AssumeRole`) with the policy above.
2. Generate access keys, share them with the engineer running CostDNA.
3. They run: `costdna doctor --aws-profile <profile>` (preflight) → `costdna scan --aws-profile <profile> --save-dir runs/eval`
4. We review predictions together, decide whether to proceed with tag application.

Total commitment from your side: ~30 minutes of meeting time over the course of a day.

---

**Repo**: https://github.com/pauti04/CostDNA  
**Live demo**: https://cost-dna.vercel.app

If anything's unclear, ping me — happy to do a 15-minute call to walk through it.
