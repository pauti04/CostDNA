# I built a 97% accurate cloud-cost ML model. Then I audited it. It was a tautology.

*Draft. Edit freely — make sure the voice is yours before you ship it.*

---

The pitch was simple: **40-60% of AWS spend is untagged**. Existing FinOps tools (CloudHealth, Vantage, Apptio) are tag-based, so they go blind on that half. I'd build the missing input layer — a Graph Neural Network that infers which team owns each resource from behavioral fingerprints (CloudTrail events, IAM access patterns, VPC flow logs, deploy timing). Run it once, write tags back to AWS, and your existing dashboard suddenly explains 90% of spend instead of 50%.

The technical bet was that **graph-aware learning would beat feature-only baselines** on the hard cases — shared services, cross-team resources, ownership reassignments — where tags drift and metadata lookup fails.

I built it. I tested it on Microsoft's published 2.6M-VM Azure trace. **97% accuracy.**

Then I audited it.

## The audit

The Azure dataset has a column called `deployment_id`. I'd been using it as a graph edge — the rationale being "resources deployed together probably belong to the same team." Reasonable.

I ran a one-line check:

```python
deployments_per_subscription = (
    df.groupby("deployment_id")["subscription_id"].nunique()
)
print((deployments_per_subscription == 1).mean())
# → 1.0
```

**Across all 33,205 deployments in the dataset, every single one mapped 1:1 to exactly one subscription.** The "graph edge" was a perfect lookup. My GNN's 97% wasn't learning behavioral patterns — it was reading the answer off a database join.

When I disabled the deployment_id edge, accuracy collapsed:

| | First-cut | Honest (no leak) | Random |
|---|---|---|---|
| LabelProp | 97% | 20% | 20% |
| GraphSAGE (5 teams) | — | 35% | 20% |
| GraphSAGE (100 teams) | — | **6.9%** | 1% |

GraphSAGE still beats random and beats every feature-only baseline at 100 classes (12× lift), but the absolute ceiling on this dataset is far lower than the original number suggested.

## I checked the second dataset. Same pattern.

Microsoft Philly is a published dataset of 117K real ML training jobs across 15 virtual clusters. Different shape from Azure — these are short-lived jobs, not long-running VMs.

Same audit:

```python
users_per_vc = df.groupby("user_id")["vc"].nunique()
print((users_per_vc == 1).mean())
# → 0.85
```

**85% of users belong to exactly one VC.** Not 100% — but close enough that `user_id` is a near-tautological signal for `vc`. With user edges enabled, GraphSAGE hits 71.5%. Strip them and it falls to 15%.

Two datasets. Two different shortcuts. One consistent finding: **production cloud attribution is mostly a metadata-lookup problem.** The dominant signal is structural — deployment IDs, IAM principals, machine assignments — not behavioral time-series. Behavioral fingerprinting matters specifically when metadata is missing or unreliable.

## The pivot

The audit changed what the project even was. The original framing — "we beat the baseline by X%" — collapsed. The honest framing was awkward: a careful negative result.

But the negative result was the actually-defensible thing in the repo. So I made it the centerpiece. The methodological contribution isn't "GNN beats label propagation by 5 percentage points." It's **"first-cut accuracy on cloud datasets is almost certainly inflated by graph leakage; here's the audit pattern; here's what the honest number looks like; here's the regime where behavioral fingerprinting actually matters."**

Then I built the regime where it matters: a synthetic AWS environment with four teams, four resource types, and five deliberately-hard "kinds":

- **`shared_service`** — Backend's RDS hammered by data + ml (~65% cross-team callers). Behavioral features point the wrong direction.
- **`cross_team`** — Used roughly equally by two teams. Same problem.
- **`reassigned`** — Team A owned it for 7 days; team B took over. Time-window features blend.
- **`sparse`** — Cold-storage S3, infrequent Lambdas. Few events → unstable fingerprint.
- **`clean`** — Easy. Any model gets these.

On the synthetic env, GraphSAGE hits 95%+ while feature-only baselines fail catastrophically on `cross_team` (LogReg: 0% across 5 seeds). The methodology validates *under conditions the methodology is designed for* — which is the only honest claim you can make.

## Pivot 2: from research artifact to product

A folder of charts and benchmark tables is a paper, not a product. So I added the layer that turns the model into something a FinOps engineer can actually use: **a natural-language agent.**

```bash
$ costdna ask "why did our bill spike Tuesday?"

Resource `mlops-rds-002` (predicted team: ml, conf 0.92) had a $9.43
cost spike at Wed 01:00. Team ml's deploy at Tue 23:28 (commit ae5a13c,
repo ml-svc) is the most likely cause (Granger p=0.000).
```

The agent has 9 tools — `summarize_account`, `attribute_resource`, `top_spenders`, `find_cost_spikes`, `find_anomalies`, etc. The LLM (GPT-4o on the live demo, Claude in the local CLI) decides which to chain based on the question. This is the actual product — the GraphSAGE model is now an implementation detail.

**Live demo: [cost-dna.vercel.app](https://cost-dna.vercel.app).** Synthetic 68-resource account. Click a suggestion, get a real answer with real dollars and resource IDs. ~$0.01/question on OpenAI's API.

## What I'd do differently

1. **Audit before benchmarking.** I burned time celebrating 97% before checking the dataset for leaks. The check is one line of pandas. Run it first, every time, on every dataset.

2. **Build the synthetic env early.** Real cloud datasets are uniformly messy in ways that obscure what the model is learning. I should have started from a synthetic env where I controlled feature density and label structure, validated the methodology there, *then* tested transferability.

3. **Frame the artifact as a product earlier.** A research-grade benchmark suite is invisible to anyone who isn't already deep in the field. The same model wrapped in a chat interface is something a FinOps engineer recognizes in 10 seconds.

## What's in the repo

- **9-tool LLM agent** — natural-language interface over the model's outputs
- **GraphSAGE classifier** — 4-layer, residual, with a supervised contrastive head
- **Behavioral feature extraction** — IAM patterns, VPC traffic, deploy timing, cost time-series shape
- **LLM-derived semantic features** — sentence-transformer embeddings of role names + resource IDs
- **Synthetic AWS env** — 4 teams × 4 resource types × 5 hard-case kinds, fully Terraform-able
- **Audit harness** — k-fold CV, multi-seed, ablation, calibration (ECE), reliability diagrams
- **Hardened collectors** — boto3 with adaptive retry, throttle-aware CloudTrail, AssumeRole-from-account
- **Docker image + GitHub Actions** — `docker run pauti04/costdna scan --synthetic`

Repo: **[github.com/pauti04/CostDNA](https://github.com/pauti04/CostDNA)**.

## The takeaway

If your benchmark accuracy is suspiciously high, audit the labels. If your dataset has a column that maps 1:1 (or near-1:1) to the target, you have a label leak. The fix isn't to bury the result; it's to publish the audit alongside the original number. Negative results, well-documented, are more useful than inflated positive ones.

The methodological finding ("structural metadata dominates real cloud attribution") is more durable than any specific accuracy number. Build the artifact that demonstrates *that* finding, not the artifact that hides it.
