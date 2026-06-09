# How I caught label leakage in Microsoft's 2.6M-VM Azure dataset

*A two-line `pandas` check that turned my 97% accuracy into 6.9% — and why
the honest negative result is more useful than the inflated positive one.*

**TL;DR:** I was training a graph neural network for cloud-resource
attribution on Microsoft's published Azure trace and hit 97% accuracy on a
100-class problem. That number was too good. I ran a two-line audit:

```python
(df.groupby("deployment_id")["subscription_id"].nunique() == 1).mean()
# → 1.0
```

Across all 33,205 deployments in the dataset, every single one belonged to
exactly one subscription. The graph edge I was using was a perfect lookup of
the prediction target. With the leak removed, honest accuracy on 100 classes
was **6.9%** — still ~7× random, still beats every non-graph baseline, but a
long way from 97%.

I think this pattern generalizes. Prior published work in cloud-resource
attribution has probably been measuring leakage rather than learning. This
post walks through the audit, the fix, and proposes a two-line check that
should be standard before reporting cloud-attribution accuracy.

---

## The setup

I was working on [CostDNA](https://github.com/pauti04/CostDNA), an open-source
graph neural network for **cloud-resource attribution** — given an AWS account
(or Azure subscription) with mostly-untagged resources, predict which team
owns each resource based on behavioral signals: CloudTrail events, IAM access
patterns, cost time-series shape, VPC flow logs. The model is a GraphSAGE
classifier over a graph where nodes are resources and edges encode
co-occurrence: same VPC, same IAM role, traffic flow, etc.

The synthetic environment I'd built was producing reasonable numbers (~90%
on 4 teams with hard-case kinds like cross-team and reassigned resources).
Time to validate on real data.

[Microsoft published a 2.6M-VM Azure trace](https://github.com/Azure/AzurePublicDataset)
covering 100 subscriptions over 30 days. The largest publicly available cloud
trace. I downloaded it, mapped it into CostDNA's data model, and ran the full
pipeline.

## The result that was too good

LabelProp scored **97% accuracy across 5–100 teams**. GraphSAGE was a bit
behind at ~92%.

A 97% number on a 100-class problem (random = 1%) should make you suspicious.
State-of-the-art results on much easier ML problems rarely beat 95%. Either
my graph neural network had quietly solved cloud attribution, or something
about my evaluation was structurally wrong.

The first response to a too-good result is to celebrate. The second is to
audit. I audited.

## The two-line check

The intuition: cloud datasets have many columns that *could* be graph edges,
*could* be features, or *could* be the prediction target. If two of them
deterministically encode the same information, using one as an edge and the
other as a target makes the "prediction" task into a database join.

The check:

```python
import pandas as pd

# For each candidate edge column, check whether it deterministically maps to the target
for edge_col in ["deployment_id", "vm_category", "machine_type", "role"]:
    determinism = (df.groupby(edge_col)["subscription_id"].nunique() == 1).mean()
    print(f"{edge_col}: {determinism:.3f}")
```

Output on the Azure trace:

```
deployment_id: 1.000
vm_category:   0.142
machine_type:  0.031
role:          0.198
```

**`deployment_id` was 1.000.** Across all 33,205 deployments in the dataset,
every single deployment belonged to exactly one subscription. Using
`deployment_id` as a graph edge meant the model could look up the
subscription via deployment with 100% confidence — no learning required.

LabelProp's "97%" was a graph-database join, not learning.

## The fix and the honest number

Remove the leaking edges from the graph. Re-run.

GraphSAGE on 100 classes: **6.9%** — still ~7× random (random = 1%), still
beats every feature-only baseline including node2vec (which was tied with
plain logistic regression at ~3% on this regime), but a long way from 97%.

Here's the post-audit table:

| N teams | Random | LogReg | k-NN | LabelProp | GraphSAGE |
|---|---|---|---|---|---|
| 5 | 20% | 31.3% | 28.6% | 20.0% | **34.6%** |
| 10 | 10% | 18.3% | 17.3% | 10.0% | **22.4%** |
| 25 | 4% | 9.2% | 10.0% | 4.0% | **10.6%** |
| 100 | 1% | 3.4% | 3.8% | 1.0% | **6.9%** |

GraphSAGE wins consistently but the absolute numbers are modest, because the
Azure trace ships only summary CPU statistics (max/avg/p95) per VM — not the
full hourly time-series files (those total 140GB and aren't ingested). With
richer per-resource features the gap would be larger.

## I ran the same audit on a second dataset

To check whether this was a one-off Microsoft Azure quirk or a pattern, I
ran the same audit on [Microsoft Philly](https://github.com/msr-fiddle/philly-traces),
a 117K-DL-job trace from Microsoft Research's internal ML training cluster.
Different domain (jobs, not VMs), different time period, different team
(MSR Fiddle), different attribution task (15 virtual clusters instead of
100 subscriptions).

Audit output:

```
user_id: 0.850
machine_id: 0.014
...
```

`user_id` was 0.85 — 85% of users in the dataset belong to exactly one
virtual cluster. Not 100% deterministic like Azure, but high enough that
the graph edge does most of the work. With the user-edge removed, GraphSAGE
on 15 classes drops from 89% to 14% (still 2× random).

**Two unrelated public datasets, same pattern.** The structural metadata
columns (deployment IDs, user IDs, IAM principals) deterministically encode
the prediction target. Any graph-based attribution that uses these as edges
is doing a join, not learning.

## The thesis

I think this pattern generalizes. **Prior published work in cloud-resource
attribution has likely been measuring leakage rather than learning.**

The reasoning:

1. Both Azure and Philly were published by Microsoft Research, with full
   schema documentation, and were heavily used by other researchers.
2. The leak in Azure is a one-line check away; it shouldn't have survived
   peer review unless reviewers also didn't run the check.
3. The same pattern in a second, structurally-unrelated dataset suggests
   it's not a Microsoft-specific bug — it's a property of how cloud data
   is generated. Engineering teams provision resources in deployments,
   and those deployments are scoped to single subscriptions/projects.
   The metadata reflects this org structure.

So if your cloud-attribution paper uses `deployment_id` (or `request_id`,
or `user_id`, or `cluster_id`) as a graph signal without running the audit,
your reported accuracy is probably high because of structural leakage,
not because of behavioral signal. Behavioral attribution on its own —
without the structural shortcuts — is much harder.

This is a falsifiable claim. If a cloud-attribution paper exists that runs
the audit and reports honest behavioral numbers above 50% on 100-class
attribution, I'd love to read it.

## The two-line standard

I propose the following as a minimum standard before reporting any
cloud-attribution accuracy:

```python
def find_deterministic_edges(
    df: pd.DataFrame,
    target_col: str,
    candidate_edge_cols: list[str],
    threshold: float = 0.85,
) -> dict[str, float]:
    """Edge columns that deterministically encode the target = leaks."""
    out = {}
    for col in candidate_edge_cols:
        determinism = (df.groupby(col)[target_col].nunique() == 1).mean()
        if determinism >= threshold:
            out[col] = determinism
    return out
```

Run this on your dataset before training. If any edge column has determinism
≥ 0.85, you have a leak — using that edge as a graph signal will inflate
model accuracy in a way that doesn't reflect what the model has learned.

Cost: one function call. Catches the failure mode this post documents on
two unrelated public datasets.

## What I'd hoped the result would be

This is the part the ML-paper format usually leaves out: the gap between
"what I hoped to find" and "what I actually found."

I'd hoped: a strong positive result. "Behavioral GNN attribution achieves
90%+ accuracy on Microsoft's published Azure dataset, beating LogReg by 30
points." Standard ML paper.

I got: a strong methodological negative result. "Two published cloud datasets
have label leakage that inflates first-cut accuracy by 60–90 percentage
points. With leaks removed, honest behavioral accuracy is modest. Prior work
is probably measuring leaks."

The negative result is more useful. The positive result would have been one
more cloud-attribution paper with the same hidden weakness as the others.
The negative result is a methodology critique that, if even partially right,
saves the next team six months of chasing the wrong baseline.

## What I'm not claiming

To be clear about the scope:

- **I'm not claiming behavioral cloud attribution doesn't work.** It works
  on the synthetic env where features are rich; it likely works on real
  production AWS accounts with full CloudTrail. What I'm claiming is that
  *the public datasets used to evaluate it don't have the feature density
  to demonstrate the claim convincingly.*
- **I'm not claiming all prior cloud-attribution work is wrong.** I'm
  claiming that the published datasets most commonly used (including the
  two I audited) have the label-leakage pattern. Any specific paper that
  ran the audit and avoided the leak is fine; I just haven't found one.
- **I'm not claiming the audit is novel.** Label leakage is a well-known
  ML failure mode. What's specific to cloud-attribution is the *form* of
  the leak — structural metadata (deployment IDs, user IDs) is so close
  to the prediction target in cloud datasets that it's easy to accidentally
  include as a graph edge.

## What I'm asking

If you work on cloud-cost ML, cloud-resource attribution, or anything
adjacent: **run the audit on your own datasets.** Two lines. If it doesn't
trigger, your numbers are honest. If it does, you've just saved yourself
the post-deployment surprise.

If you know of a public cloud-attribution dataset that has rich behavioral
features AND no structural-metadata leak, please [open an issue on the
CostDNA repo](https://github.com/pauti04/CostDNA/issues) or DM me. That's
the missing data point this work needs.

---

CostDNA is open-source under MIT.

Repo: [github.com/pauti04/CostDNA](https://github.com/pauti04/CostDNA) ·
Live demo: [cost-dna.vercel.app](https://cost-dna.vercel.app) ·
Methodology paper draft: [docs/limitations.md](https://github.com/pauti04/CostDNA/blob/main/docs/limitations.md)

I'm Parth Auti. I'm currently looking for full-time roles in cloud-cost /
FinOps / ML-infra. If this work resonates, I'd like to chat — DMs open on
[LinkedIn](https://linkedin.com/in/) and [GitHub](https://github.com/pauti04).
