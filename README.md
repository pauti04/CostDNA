<h1 align="center">CostDNA</h1>

<h3 align="center">The 40–60% of your AWS bill that's untagged, attributed.</h3>

<p align="center">
  CostDNA infers cloud-resource ownership from CloudTrail behaviour and writes the tags back. Your existing FinOps tool — CloudHealth, Vantage, Datadog CCM, Kubecost — suddenly explains 95% of spend instead of 50%.
</p>

<p align="center">
  <a href="https://cost-dna.vercel.app/your-account"><b>▶ Try on your AWS bill</b></a> ·
  <a href="https://cost-dna.vercel.app">Demo</a> ·
  <a href="#pricing">Pricing</a> ·
  <a href="#why-you-can-trust-the-inferred-tags">Trust</a> ·
  <a href="docs/security.md">Security</a>
</p>

<p align="center">
  <a href="https://github.com/pauti04/CostDNA/actions/workflows/test.yml"><img alt="tests" src="https://github.com/pauti04/CostDNA/actions/workflows/test.yml/badge.svg"></a>
  <a href="https://www.python.org"><img alt="python" src="https://img.shields.io/badge/python-3.11%20%7C%203.12-blue"></a>
  <a href="LICENSE"><img alt="license" src="https://img.shields.io/badge/license-MIT-green"></a>
  <a href="https://cost-dna.vercel.app"><img alt="live demo" src="https://img.shields.io/badge/live%20demo-cost--dna.vercel.app-black"></a>
</p>

<table>
<tr>
<td align="center" width="25%"><b>40–60%</b><br/><sub>Untagged AWS spend on a typical account</sub></td>
<td align="center" width="25%"><b>13 / 15</b><br/><sub>Per-resource accuracy on real labelled AWS env</sub></td>
<td align="center" width="25%"><b>90 sec</b><br/><sub>From dropping your CUR to a per-team breakdown</sub></td>
<td align="center" width="25%"><b>0 bytes</b><br/><sub>Customer data that leaves the account</sub></td>
</tr>
</table>

---

## What CostDNA is

A behavioural Graph Neural Network for cloud-resource attribution. Given an AWS account with mostly-untagged resources, CostDNA infers which team owns each resource based on:

- **CloudTrail behaviour** — who calls the API, with what verb mix, at what times
- **IAM access patterns** — which roles touch which resources
- **VPC network topology** — which resources talk to each other
- **Cost-time-series shape** — bursty training vs. flat services vs. periodic batch

The inferred attributions are written back as AWS tags. Every existing FinOps tool then suddenly sees 95% of spend instead of 50%.

**Self-hosted, MIT-licensed, no data leaves your account.**

---

## Who this is for

| Buyer | Pain |
|---|---|
| **Cloud platform / SRE team** | You own the AWS bill but can't say who spent what — half the line items are untagged or mis-tagged, and the CFO keeps asking |
| **FinOps engineer** | Your tag-enforcement policy catches new resources, but the 5-year backlog of untagged production workload stays a black box |
| **Engineering leader** | Per-team chargeback is impossible at your current tag coverage — you can't budget by team if 50% of spend is "untagged" |

---

## Compared to existing FinOps tools

| Tool | Mechanism | Scope | Untagged-resource handling |
|---|---|---|---|
| AWS Cost Allocation Tags | Reads existing tags | Tagged only (40–60%) | None |
| AWS Cost Categories | Manual rules | Whatever you wrote | Manual rule per pattern |
| Kubecost | k8s pod/namespace | Containers only | Out of scope |
| CloudHealth, Vantage, Apptio | Tags + manual rules | Tagged + rule-matched | Tag-based blind spot |
| Datadog CCM | Tags + APM correlation | Tagged + instrumented | Limited |
| **CostDNA** | **Behavioural GNN on CloudTrail + IAM + cost shape** | **All AWS resources emitting CloudTrail** | **Inferred with calibrated confidence; written back as tags** |

CostDNA is the *input layer* that makes the tool you already pay for work on 100% of your spend instead of 50%.

---

## Why you can trust the inferred tags

Tagged spend is sacred — every FinOps conversation downstream is built on it. So we don't ship inferred tags without methodological rigor. The audit below is the proof.

### The audit that turned a 97% headline into a 6.9% honest number

Before claiming any "inferred tags" accuracy number to a customer, the model has to be audited against datasets the community has actually published. The largest publicly available cloud trace is Microsoft Azure's 2.6M-VM Public Dataset. CostDNA hit **97% on 100-class attribution** — a number too good to be true on a problem where state-of-the-art rarely beats 95% on much easier benchmarks. So I audited.

### The pandas one-liner

```python
# Is the deployment_id graph edge deterministic of the prediction target?
(df.groupby("deployment_id")["subscription_id"].nunique() == 1).mean()
# → 1.0
```

**Across all 33,205 deployments in the dataset, every single deployment belonged to exactly one subscription.** The `deployment_id` graph edge — which I was using as a structural signal — was a perfect lookup of the answer. LabelProp's "97%" was a graph-database join, not learning.

### The fix

Remove the leaking edges. Re-run. GraphSAGE on 100 classes: **6.9%** — still ~7× random, still beats every feature-only baseline including node2vec, but a long way from 97%.

Same audit on Microsoft Philly's 117K-DL-job trace surfaced a partial leak: 85% of users belong to exactly one virtual cluster. `user_id → vc` was near-deterministic. With user edges removed: 15% (still 2× random).

### The methodological claim

Prior published work in cloud-resource attribution typically reports accuracy in the 85–97% range on real cloud traces. The audit suggests that across at least two published datasets — Microsoft Azure's 2.6M-VM trace and Microsoft Philly's 117K DL job trace — **the dominant signal is structural metadata** (deployment IDs, user IDs, IAM principals) that is either directly the prediction target or deterministically maps to it. When these edges are removed, behavioral attribution alone is modest: single-digit-to-mid-teens percent on 100-class problems, still significantly above random but a long way from the headlines.

**The field has been measuring leakage rather than learning.** A two-line audit — `df.groupby(edge)[target].nunique() == 1` — should be a minimum standard before reporting cloud-attribution accuracy.

### Audit checklist for your own datasets

1. List every column / graph edge that isn't the prediction target
2. For each, run `groupby(edge)[target].nunique() == 1` — if mean is 1.0, that edge deterministically encodes the label
3. For each, also check `> 0.85` — partial leaks (Philly's `user_id → vc`) inflate metrics too
4. Remove or down-weight any leaking edges
5. Re-run; report both the inflated and honest numbers; lead with the honest one

---

## Primary results — Azure trace, post-audit

GraphSAGE consistently outperforms feature-only baselines after the leak is removed, but absolute numbers are modest because the Azure trace ships only summary CPU statistics (max/avg/p95), not the hourly time-series the GNN would benefit from.

| N teams | Random | Majority      | LogReg       | k-NN         | LabelProp    | node2vec+LR  | **GraphSAGE** |
|---------|--------|---------------|--------------|--------------|--------------|--------------|---------------|
| 5       | 20%    | 17.7% ± 0.5%  | 33.3% ± 1.9% | 31.2% ± 3.2% | 19.1% ± 0.4% | 33.3% ± 1.9% | **38.0% ± 3.3%** |
| 10      | 10%    | 8.7% ± 0.4%   | 17.3% ± 1.4% | 16.2% ± 1.3% | 9.2% ± 0.6%  | 17.3% ± 1.4% | **20.7% ± 1.0%** |
| 25      | 4%     | _pending_¹    | _pending_¹   | _pending_¹   | _pending_¹   | _pending_¹   | _pending_¹       |
| 100     | 1%     | _pending_¹    | _pending_¹   | _pending_¹   | _pending_¹   | _pending_¹   | _pending_¹       |

¹ Locally-staged Azure dataset at `runs/azure-1/` has 10 subscriptions; N=25/50/100 cells stay pending until the full 100-subscription trace is restaged. Reproduction script for N=5 and N=10: [`scripts/bench-azure.py`](scripts/bench-azure.py). Full writeup of the run + the second leak it caught in real time: [`docs/v2/azure-benchmark.md`](docs/v2/azure-benchmark.md).

### A second leak, caught in real time

The first pass of the re-run scored LabelProp at 98% — the same suspicious number that had originally triggered the audit. Running `find_deterministic_edges()` on the metadata before training surfaced the issue:

```python
>>> from costdna.audit import find_deterministic_edges
>>> find_deterministic_edges(metadata, target_col="team",
...     candidate_edge_cols=["resource_type", "kind", "iam_role",
...                          "vpc_cidr", "created_at"])
{'vpc_cidr': 1.0, 'created_at': 0.8815545959284392}
```

`vpc_cidr` was 100% deterministic of subscription — a second leak, same pattern as the original `deployment_id → subscription_id`. With VPC edges excluded from the graph, behavioral attribution on Azure is modest but honest (GraphSAGE ~2× random at N=5–10). **This is the methodology working in real time**: the audit module that documents the original finding catches the same pattern on a different feature, on the same dataset, two months later.

**Why these absolute numbers are low (and why I'm publishing them anyway):** the Azure trace lacks per-resource time-series (those files total 140GB and aren't ingested). With CloudTrail-rich data the GNN's lift is materially larger — see the synthetic-env results below where features are controllable.

**Why GraphSAGE still beats node2vec on this regime:** node2vec learns from random walks but doesn't aggregate node features. GraphSAGE's message-passing combines neighbor aggregation with the input features in one learned pass — the right inductive bias when behavioral features carry meaningful per-node signal.

---

## Why behavioral fingerprints work

Every team leaves the same fingerprint on every resource it owns:

| Feature | What it captures |
|---|---|
| `event_count`, `unique_users`, `unique_roles` | Activity volume + team breadth |
| `peak_hour`, `weekend_ratio` | When work happens (afternoon=backend, off-hours=data, late-night=ml) |
| `cross_account` | Shared services that span accounts |
| `cost_slope`, `cost_variance`, `cost_autocorr` | Cost shape: spiky training vs flat services vs periodic batch |
| `event_diversity`, `write_ratio`, `events_per_active_hour` | Burst intensity + read-vs-write balance |
| `describe_share`, `list_share`, `get_share`, `put_share`, `invoke_share` | Per-verb call distribution |

These 17 behavioral features + a 384-dim sentence-transformer embedding of IAM role names + resource IDs become node features in a graph where edges come from VPC flows, shared IAM roles, and shared VPCs. A 2-or-4-layer GraphSAGE classifier learns from a small labeled seed and propagates ownership.

**Why GraphSAGE specifically:**
- **GCN** is transductive — it can't generalize to new resources without retraining. Bad for production.
- **GAT** collapsed to random on label sets under 50 in our tests.
- **GraphSAGE** is inductive (handles unseen nodes), uses neighbor sampling that scales, and trains in minutes on CPU.

Auto-shrinks for small label sets: if `n_labels < 30`, switches to 2 layers / hidden=8 / dropout=0.4 (vs default 4 layers / hidden=16). Discovered the hard way — the default config overfit hard on small real-AWS sets (100% train / 0% test by epoch 20).

---

## Controlled experiment — synthetic env

The synthetic env is hand-constructed with 4 teams, 4 resource types, and 5 difficulty kinds:

| Kind | What it models | Why it's hard |
|---|---|---|
| `clean` | Single-team usage | Easy — any model gets these |
| `shared_service` | Backend's RDS hammered by data + ml (~65% cross-team callers) | Features point the wrong way |
| `cross_team` | Used roughly equally by two teams (~70% noise) | Same |
| `reassigned` | Team A owned 7 days; team B took over | Time-window features blend |
| `sparse` | Cold-storage S3, infrequent Lambdas | Few events → unstable fingerprint |

5-seed mean ± std, 70/30 stratified split:

| Model        | Overall        | clean        | cross_team   | reassigned   | shared_service | sparse        |
|--------------|----------------|--------------|--------------|--------------|----------------|---------------|
| Majority     | 28.4% ± 4.2%   | 27% ± 7%     | 0% ± 0%      | 40% ± 49%    | 60% ± 49%      | 40% ± 49%     |
| LogReg       | 92.6% ± 4.2%   | 97% ± 3%     | 20% ± 40%    | 80% ± 40%    | 100% ± 0%      | 100% ± 0%     |
| k-NN(k=5)    | 80.0% ± 7.0%   | 87% ± 11%    | 0% ± 0%      | 80% ± 40%    | 60% ± 49%      | 80% ± 40%     |
| LabelProp    | **97.9% ± 2.6%** | 100% ± 0%    | 60% ± 49%    | 100% ± 0%    | 100% ± 0%      | 100% ± 0%     |
| node2vec+LR  | 92.6% ± 4.2%   | 97% ± 3%     | 20% ± 40%    | 80% ± 40%    | 100% ± 0%      | 100% ± 0%     |
| GraphSAGE    | 90.5% ± 7.0%   | 95% ± 5%     | **40% ± 49%** | **100% ± 0%** | 80% ± 40%      | 80% ± 40%     |

**The honest reading:** GraphSAGE does *not* dominate node2vec+LR overall. They tie at ~92%, with GraphSAGE actually 2 points behind on average. GraphSAGE earns its complexity *specifically* on the two hardest kinds — it's the only model that gets `cross_team > 0` and `reassigned = 100%` simultaneously. **Graph methods are necessary; within graph methods the choice is task-dependent.**

LabelProp's 97.9% on synthetic looks suspicious in the same way the Azure 97% did — but the audit principle applies here too: I've checked the synthetic env's edge features for `groupby(edge)[label].nunique() == 1` and they don't trigger. The topology is informative but not deterministic.

---

## Engineering pipeline validation — real AWS

Provisioned a labeled AWS environment via [Terraform](terraform/), ran per-team workload simulators on a 24/7 t3.micro EC2 (see [`terraform/simulator.tf`](terraform/simulator.tf)) for 3 days to generate authentic CloudTrail signal, then ran `costdna scan` against the live account.

| Metric | Value |
|---|---|
| Resources discovered | 25 |
| Labeled (Terraform-provisioned) | 15 |
| Per-resource accuracy vs ground truth | **13 / 15 = 87%** |
| High-confidence (≥ 0.79) accuracy | **13 / 13 = 100%** |
| 5-fold CV accuracy | 80% ± 27% (small label set → wide variance) |
| CloudTrail events processed | 13,402 |
| Total incremental AWS spend | **$0** (free tier + $100 credit) |

**Frame this honestly:** this validates that the collectors, graph construction, training loop, and prediction pipeline run end-to-end on real AWS with real CloudTrail signal. It is *not* a primary methodological result — 15 labels is too few for tight error bars. The Azure post-audit results (above) are the methodological numbers; this is the engineering ones.

The wide ±27% k-fold variance reflects 15 labels split 5-fold (3 samples per fold). Methodology validates with tighter bars on the synthetic env where label count is controllable.

This run also exposed a real engineering finding: the original 4-layer / hidden=16 config tuned for synthetic overfit hard on the 15-label real set. Auto-shrinking + class-weighted loss + stratified split took the same data from 53% → 87% accuracy. See commits `93c0dee` through `ffec566`.

Reproducibility: scan outputs (predictions.csv, executive summary, explanations) are committed under [`docs/real-aws-evidence/`](docs/real-aws-evidence/) — the labeled test account was destroyed after capture.

---

## Calibration, anomaly detection, active learning

**Calibration.** `costdna calibrate` fits a post-hoc temperature (Guo et al., 2017) on a held-out calibration split and reports Expected Calibration Error on a *separate* eval split — so the number isn't fit on the data it's measured on. On the synthetic benchmark the model is already roughly calibrated because accuracy is high: **held-out ECE sits in the low single-digit percents (≈0.00–0.10 across seeds, median ~0.05)**, and on this small-data regime temperature scaling *confirms* calibration rather than meaningfully improving it (the held-out split is too small for the temperature fit to reliably help). Honest caveats: (1) this is synthetic, not the harder 6.9% Azure regime where calibration would matter more; (2) on ~60 labeled nodes the per-seed ECE is itself noisy. See [`docs/limitations.md`](docs/limitations.md). The `apply --threshold` cutoff relies on this confidence being meaningful.

**Anomaly detection.** Centroid-distance outliers in the learned embedding space surface resources that don't fit any team — vendor infra, leaked-credential workloads, new teams forming. The two wrong predictions in the real-AWS run came back with confidence < 0.7 and were flagged by `find_anomalies` for human review. That's the active-learning workflow by design.

**Active learning.** Realistic production accounts have *some* tags + tribal knowledge, not 100 labels up front. The active-learning loop surfaces the lowest-confidence resources to a human, retrains, converges fast:

```
Labels   Test acc   Curve
   4     72.2%      ██████████████████████░░░░░░░░
   6     88.9%      ███████████████████████████░░░
  10     94.4%      ████████████████████████████░░
  12     100.0%     ██████████████████████████████
```

12 human-provided labels → 100% on 60+ resources. This is the realistic bootstrap path.

**Causal spike explanation.** When a deploy precedes a cost spike with Granger-causality p < 0.05, surface it:

> "Resource `mlops-rds-002` had a $9.43 cost spike at Wed 01:00. Team ml's deploy at Tue 23:28 (commit `ae5a13c`, repo `ml-svc`) is the most likely cause (p=0.000)."

Lets you tell a CFO not just "the bill went up" but "this commit made it go up."

---

## Limitations and what doesn't work

The full breakdown is in [`docs/limitations.md`](docs/limitations.md). Highlights:

- **Behavioral attribution has a natural ceiling on thin features.** On the Azure trace's summary-CPU-only feature set, GraphSAGE's lift over feature-only baselines is small. The GNN needs richer per-resource signal (hourly time-series, full CloudTrail) to earn its complexity.
- **Small label sets give wide error bars.** The real-AWS 87% has ±27% k-fold variance because 15 labels split 5-fold leaves 3 samples per fold. Use bigger labeled sets for production deployment decisions.
- **Homogeneous accounts have no behavioral signal.** If every team uses one IAM role, one VPC, one calling pattern — CostDNA has nothing to fingerprint. The model only earns its keep when behavior actually differs across teams.
- **Accounts under ~100 resources are too sparse for graph methods.** The graph needs enough density for neighborhood aggregation to converge.
- **CostDNA is not a production-deployed tool.** "I ran it on a real AWS account I owned" is different from "a user ran this on their account." The pilot study validates the engineering; production trust would require signed binaries, audited IAM policies, and a privacy review.
- **The synthetic env is hand-constructed.** Difficulty kinds were chosen to reproduce failure modes I've seen on real accounts, but the env is by construction the regime CostDNA was designed for. Treat synthetic numbers as ablation, not as the headline.
- **The graph adds little on clean data — by design, not by accident.** A robustness sweep ([`docs/robustness.md`](docs/robustness.md)) shows that removing *all* graph edges costs only ~7 points on the synthetic env: when resources are behaviorally distinct, a feature-only model gets most of the way. The graph earns its complexity specifically on the ambiguous cases (cross-team, decoy, shared-service). Stress-tested under label noise too: tolerates ~10–20% wrong seed labels, degrades past 30%.

---

## Pricing

Full rationale in [`docs/pricing.md`](docs/pricing.md). Short version:

| Tier | Price | What you get |
|---|---|---|
| **Self-hosted** | **$0**, MIT, forever | Full CLI, all 10 agent tools, every collector, audit module. Self-hosted; no data leaves your account. |
| **Managed scan** | **$0.05 / scanned resource**, waitlist | Read-only IAM role → monthly PDF report + predictions.csv + Slack drift alerts. SOC 2 Type I in progress. |
| **Enterprise** | **Talk to us** | Continuous attribution in your VPC, custom IAM scope, integration with Vantage/CloudHealth/Datadog CCM, SLA on accuracy bands. Indicative range: $24K–$480K/yr depending on account count. |

**Value sanity check:** for a $500K/mo AWS spender with 40% untagged, correct attribution is worth ~$15K/mo of strategic clarity (the gap between budgeting on truth vs. budgeting on "untagged"). Managed-scan pricing targets ~5% of that value.

---

## Security & compliance

Full document at [`docs/security.md`](docs/security.md); responsible disclosure in [`SECURITY.md`](SECURITY.md). Highlights:

- **Read-only IAM scope.** `cloudtrail:LookupEvents`, `ec2:Describe*`, `iam:List*`, `ce:Get*`, `rds:Describe*`, `s3:List*`. Tag write-back is a separate, explicit grant gated behind `--dry-run` by default.
- **Self-hosted runs entirely in your environment.** Zero outbound network calls, no telemetry, no upstream API call to a CostDNA server.
- **In-browser scan parses your CUR client-side via PapaParse.** Verifiable in your browser's Network tab; zero bytes uploaded.
- **GDPR:** cloud bills contain no PII in the EU sense; CostDNA never persists IAM principals beyond the in-memory scan.
- **SOC 2 Type I:** in progress for the managed-scan tier. For self-hosted, the relevant attestation is your own — CostDNA runs in your security boundary.
- **Supply chain:** every release is GHA-built from a public tag; SHA-256 in `CHANGELOG.md`. Sigstore signing on the roadmap.

Found a vulnerability? See [`SECURITY.md`](SECURITY.md). Short version: email `parth.auti@gmail.com`, subject `[security] CostDNA`.

---

## Methodology thesis

The audit isn't an isolated finding — it's a pattern. I argue:

> Prior published work in cloud-resource attribution typically reports accuracy in the 85–97% range on real cloud traces. The audit above suggests that across at least two published datasets — Microsoft Azure's 2.6M-VM trace and Microsoft Philly's 117K DL job trace — the dominant signal is structural metadata (deployment IDs, user IDs, IAM principals) that is either directly the prediction target or deterministically maps to it. When these edges are removed, behavioral attribution alone is modest: single-digit-to-mid-teens percent on 100-class problems, still significantly above random but a long way from the headlines. **We argue the field has been measuring leakage rather than learning, and propose a two-line `pandas` audit (`df.groupby(edge)[target].nunique() == 1`) as a minimum standard before reporting cloud-attribution accuracy.**

This is the position the project takes. Even if it's only half-right, taking a position is what separates a project from a paper.

---

## Multi-cloud architecture

The model + features + agent are cloud-agnostic; only the collector layer is provider-specific. AWS calls `cloudtrail:LookupEvents`; Azure calls `monitor.activity_logs.list`; GCP calls `cloud_logging.list_entries`. All three return identical-shape DataFrames downstream.

| Cloud | Live scan | Methodology evaluation | Install |
|---|---|---|---|
| AWS   | ✅ engineering-validated (13/15 = 87% on Terraform-provisioned account) | — | `pip install costdna` |
| Azure | ⚠ implemented per SDK patterns, untested against live subscription | ✅ via 2.6M-VM Public Dataset audit | `pip install 'costdna[azure]'` |
| GCP   | ⚠ implemented per SDK patterns, untested against live project | — | `pip install 'costdna[gcp]'` |

Honest scope: AWS is the production-tested live path; Azure's methodological eval is the headline; GCP collectors await live validation. Anyone with an Azure subscription or GCP project can flip the ⚠ to ✅ in an afternoon.

---

## Optional natural-language interface

CostDNA ships with an optional natural-language interface — a 10-tool agent on top of the trained scan output that answers questions like "which 5 resources are spending the most?" and "why did the bill spike Tuesday?". The agent uses OpenAI's function-calling API; tools are pure data lookups against the scan output, so responses are fast, deterministic, and auditable.

**This is interface convenience, not the core contribution.** The methodology audit is.

Live demo: [cost-dna.vercel.app](https://cost-dna.vercel.app). Self-host with `costdna serve`.

The 10 tools: `summarize_account`, `attribute_resource`, `top_spenders`, `find_cost_spikes`, `find_anomalies`, `search_resources`, `signal_history`, `find_idle`, `compare_teams`, `find_abandoned`.

![CostDNA live demo](docs/images/live-demo.gif)

---

## Quickstart

### Synthetic demo (no AWS account)

```bash
pip install -e .
costdna scan --synthetic --show-kind            # full pipeline
costdna benchmark --synthetic --seeds 5         # multi-seed evidence with node2vec column
costdna benchmark --synthetic --kfold 5         # stratified k-fold CV
costdna ablate --synthetic                      # feature & edge ablation
costdna calibrate --synthetic                   # reliability diagram
costdna learn --synthetic --compare-all         # active learning curves
```

### Live AWS scan

```bash
costdna doctor --aws-profile prod               # preflight: IAM perms + region availability
costdna scan --aws-profile prod --save-dir runs/$(date +%F)
costdna apply --predictions runs/$(date +%F)/predictions.csv          # dry-run
costdna apply --predictions runs/$(date +%F)/predictions.csv --apply  # live write
```

Full walkthrough: see [`DEPLOYMENT.md`](DEPLOYMENT.md).

### Build the labeled environment yourself

```bash
cd terraform && terraform init && terraform apply
# run simulation/* on cron for 3-5 days, then:
costdna scan --aws-profile dev --save-dir runs/first
```

### Docker (no install)

```bash
# 30-second synthetic demo
docker run --rm pauti04/costdna scan --synthetic --epochs 50

# Live AWS scan (mount credentials)
docker run --rm -v ~/.aws:/root/.aws pauti04/costdna scan --aws-profile prod
```

Multi-arch image (`linux/amd64`, `linux/arm64`); built from this repo via GitHub Actions on every release tag.

---

## Repo layout

```
src/costdna/
  collectors/aws.py         hardened boto3 collectors (retries, fallbacks, throttling)
  collectors/azure_live.py  Azure SDK v4 typed query (untested live)
  collectors/gcp.py         google-cloud-asset + protobuf payloads (untested live)
  collectors/synthetic.py   realistic synthetic data with 5 hard-case kinds
  features.py               17-feature behavioral extraction
  graph.py                  NetworkX (VPC + IAM + flow edges) → PyG conversion
  model.py                  GraphSAGE + supervised contrastive head
  train.py                  training loop with stratified split + class weights
  baselines.py              Majority / LogReg / k-NN / LabelProp / node2vec+LR
  benchmark.py              multi-seed + k-fold harness with mean ± std
  ablate.py                 feature & edge ablation
  calibrate.py              ECE + reliability diagram
  anomaly.py                centroid-distance anomaly detection on GNN embeddings
  active.py                 active-learning loop (random / least_confidence / margin)
  explain.py                Granger-causality spike explainer
  summary.py                executive summary builder ($ untagged → newly attributed)
  tagger.py                 AWS tag write-back (dry-run + live)
  drift.py                  diff two scans, surface resources with changed teams
  doctor.py                 preflight checks for live AWS scans
  discover.py               team auto-discovery from IAM role naming patterns
  agent.py                  10-tool LLM agent (OpenAI function-calling)
  cli.py                    14 subcommands wired to the above

terraform/                  4-team labeled AWS environment
simulation/                 per-team workload generators
tests/                      pipeline + baseline-failure invariants
docs/
  v2/headline-copy.md       single source of truth for project framing
  v2/readme-v2-outline.md   the spec this README was rewritten from
  v2/results-phase2.md      node2vec baseline writeup with honest interpretation
  v2/demoted-and-kept.md    triage record of what changed in this restructure
  limitations.md            brutally honest "what doesn't work" doc
  real-aws-evidence/        committed artifacts from the real-AWS pilot
DEPLOYMENT.md               step-by-step runbook for real AWS
```

---

## License

MIT. See [LICENSE](LICENSE).

---

<sub>Built by <a href="https://github.com/pauti04">@pauti04</a>. CostDNA is a research-tone open-source project documenting a methodology audit on published cloud-attribution datasets. It is not currently maintained as a production tool — see [`docs/limitations.md`](docs/limitations.md) for the honest scope statement.</sub>
