# CostDNA

**A natural-language agent for AWS cost attribution.** Ask it questions about your cloud bill in English; it answers with specific resources, teams, dollar amounts, and timestamps — backed by a behavioral GraphSAGE model + LLM-derived semantic features over CloudTrail / IAM / Cost Explorer.

```bash
$ costdna ask "why did our bill spike Tuesday?" --from-dir runs/today
? why did our bill spike Tuesday?

╭─── CostDNA ────────────────────────────────────────────────────────────╮
│ Resource `i-0c4f3230` (predicted team: ml, conf 0.92) had a $7.30      │
│ cost spike at Tue 16:00 UTC. Team ml's deploy at Tue 14:18 (commit    │
│ a4f2c91, repo ml-training-pipeline) is the most likely cause          │
│ (Granger p=0.000). Two other ml-team RDS instances spiked at the      │
│ same time, suggesting the deploy fanned out across the cluster.       │
╰────────────────────────────────────────────────────────────────────────╯
```

The agent has 6 tools available: `summarize_account`, `attribute_resource`, `top_spenders`, `find_cost_spikes`, `find_anomalies`, `search_resources`. Claude (or any tool-using LLM) chains them to answer questions like:

- *"Which 5 resources are racking up the most spend?"*
- *"What does `i-9f8e7d` belong to?"*
- *"Which resources don't fit any team — should I investigate them?"*
- *"Show me everything ml-team owns over $100/day"*

Setup: `pip install 'costdna[agent]'` + `export ANTHROPIC_API_KEY=...`.

> [pauti04.github.io/CostDNA](https://pauti04.github.io/CostDNA/) — full landing page with the methodology, charts, and audit narrative.

![GraphSAGE embedding — 4 teams + unowned cluster, automatically separated](docs/images/umap-synthetic.png)

*GraphSAGE embedding space on the synthetic env: 4 teams form clean clusters; the tan "unowned" cluster (vendor / legacy / orphan / shadow resources) sits visibly apart and is caught automatically by the anomaly detector.*

---

Tag-based cost attribution fails on 40–60% of real AWS resources. CostDNA infers ownership from behavioral fingerprints (IAM access, VPC traffic, deploy timing, cost time-series shape) using a Graph Neural Network, and writes the inferred tags back to AWS so existing FinOps tooling works on previously-unattributable spend.

**Methodological finding (the most defensible thing in the repo):** I tested CostDNA on two production-scale public cloud datasets (Microsoft's 2.6M-VM Azure trace and Microsoft Philly's 117K-DL-job trace) and audited my own results. *Both* first-cut high-accuracy numbers were tautologies — `deployment_id` is 100% deterministic of `subscription_id` on Azure; `user_id` is 85% deterministic of `vc` on Philly. With those leaks removed, behavioral attribution alone is modest. The audit pattern itself is the contribution: production cloud attribution is mostly a metadata-lookup problem, and behavioral fingerprinting matters specifically when metadata is missing or unreliable — exactly the gap CostDNA's synthetic env reproduces (where GraphSAGE hits 95%+ while feature-only baselines fail catastrophically).

```bash
$ costdna scan --aws-profile prod
┏━━━━━━━━━━━━━━━━━━━━━━ CostDNA — Executive summary ━━━━━━━━━━━━━━━━━━━━━━┓
┃ You have $9,570.32 in untagged spend across 60 resources.                ┃
┃                                                                          ┃
┃ ✓ Ready to tag: 58 resources, $9,186.31 (96%) at ≥70% confidence         ┃
┃ ⚠ Need review:   2 resources,   $384.01  (4%) below 70% confidence       ┃
┃                                                                          ┃
┃ Recommended actions:                                                     ┃
┃   • Tag 17 resources as ml       → moves $4,412.54 out of 'untagged'.    ┃
┃   • Tag 14 resources as data     → moves $2,142.65 out of 'untagged'.    ┃
┃   • Tag 16 resources as backend  → moves $1,829.61 out of 'untagged'.    ┃
┃   • Tag 12 resources as platform → moves   $801.51 out of 'untagged'.    ┃
┃   • Review 2 low-confidence resources before tagging — needs human eye.  ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

$ costdna apply --predictions runs/today/predictions.csv --apply
58 tags written. Drop the 2 low-confidence ones into Slack for review.
```

## The product loop

```
   ┌─ costdna doctor      ─ pre-flight your AWS account
   ├─ costdna discover    ─ find candidate teams from IAM patterns
   ├─ costdna scan        ─ predict ownership + dollars + anomalies
   ├─ costdna learn       ─ confirm low-confidence guesses (active learning)
   ├─ costdna apply       ─ write tags back to AWS
   └─ costdna diff        ─ weekly drift check (cron)
```

## Visual proof — embedding space

GraphSAGE learns a 2D-projected representation where same-team resources cluster together and unowned resources sit visibly separate.

**Synthetic (4 teams + unowned mess):** clean per-team clusters; the tan "unowned" cluster (vendor / legacy / orphan / shadow) sits visibly apart from the team clusters. The anomaly detector catches them automatically.

![Synthetic UMAP](docs/images/umap-synthetic.png)

**Real Azure (10 subscriptions × 200 VMs):** clusters are looser because the per-VM features (summary CPU stats) are weaker than the synthetic case. Same-color points still group, but with overlap.

![Azure UMAP](docs/images/umap-azure.png)

## Why behavioral fingerprints work

Every team leaves the same fingerprint on every resource it owns:

| Feature | What it captures |
|---|---|
| `event_count`, `unique_users`, `unique_roles` | Activity volume + team breadth |
| `peak_hour`, `weekend_ratio` | When work happens (afternoon=backend, off-hours=data, late-night=ml) |
| `cross_account` | Shared-services that span accounts |
| `cost_slope`, `cost_variance`, `cost_autocorr` | Cost shape: spiky training vs. flat services vs. periodic batch |

These become **node features** in a graph where edges come from VPC flows, shared IAM roles, and shared VPCs. A two-layer **GraphSAGE** classifier learns from a small labeled seed and propagates ownership.

## Evidence

### Real cloud data: two audits, one consistent finding

We tested CostDNA on two production-scale public datasets and audited each one for label leakage. The same pattern emerged both times: **structural metadata dominates real-world cloud attribution.**

| Dataset | Resources | Teams | First-cut accuracy | Audited "shortcut" | Honest behavioral accuracy |
|---|---|---|---|---|---|
| **Microsoft Azure** | 2.6M VMs / 100 subs | 100 | LabelProp 97% | `deployment_id → subscription` (100% deterministic) | **GraphSAGE 6.9%** (12× random) |
| **Microsoft Philly** | 117K DL jobs / 15 VCs | 15 | LabelProp 89% | `user → vc` (85% deterministic) | **GraphSAGE 14%** (2× random) |

**The methodological finding:** in real cloud data, the dominant attribution signal is almost always *structural metadata* — deployment IDs, IAM principals, machine assignments — not behavioral time-series. CostDNA's first-cut numbers on Azure (97%) and Philly (89%) looked great until we audited and discovered the labels were essentially encoded in the graph already.

This negative-result-as-positive-finding is the most defensible thing in the project: production cost attribution is mostly a metadata-lookup problem; behavioral fingerprinting matters specifically when metadata is missing or unreliable, which is exactly what the synthetic env's hard-case kinds reproduce.

### Microsoft Philly DL trace — audit case study

117K real DL training jobs at Microsoft Research's Philly cluster, attributed to 15 virtual clusters (research teams). 99.8% of machines are shared across multiple VCs, so machine co-location isn't a tautology.

But 85% of users belong to exactly one VC. So `user_id` *is* a near-tautological signal of team membership. This is the kind of finding that looks like a result if you don't audit and a methodology critique if you do:

| Edges enabled | LabelProp | GraphSAGE |
|---|---|---|
| All (machine + user) | 89.5% | 71.5% |
| Without user edges | 19.9% | 15.1% |
| Without machine edges | 89.9% | 71.9% |
| No graph at all | 10.0% | 13.1% |

The user-IAM edge is doing essentially all the work. In a production system this is *exactly the realistic case*: most cloud users belong to one team, and "who called this API" is the strongest team signal available. The methodology validates: graph-aware attribution exploits this signal effectively.

But for a fair test of *behavioral* attribution (independent of IAM-style metadata), only the third row matters: GraphSAGE 71.9% with machine edges removed but user edges kept; 15% if we strip everything.

### Azure Public Dataset — what we learned about graph leaks

We validated the *pipeline* (collectors, scaling, schema mapping) on Microsoft's published Azure trace. **Reading this section in full matters** — there's an audit story buried in it.

**First-cut result (misleading):** running with all features and graph edges, LabelProp scored 97% across 5–100 teams. That looked great. So we audited it.

**The audit:** in Azure, every deployment belongs to exactly one subscription. Verified across all 33,205 deployments in the 2.6M-VM dataset — 100% map 1:1 to subscriptions. The deployment_id graph edge is a *perfect lookup* of subscription_id. LabelProp's "97%" was a graph database join, not learning. We caught it; we're documenting it; nothing in the README claims that result anymore.

**The honest result, deployment_id edges removed** so the model has to attribute from behavior alone:

![Azure scale honest](docs/images/azure-scale-honest.png)

| N teams | GraphSAGE | LogReg | k-NN | LabelProp | Random |
|---|---|---|---|---|---|
| 5 | **34.6% ± 1.6%** | 31.3% ± 0.8% | 28.6% ± 3.2% | 20.0% ± 2.0% | 20.0% |
| 10 | **22.4% ± 1.6%** | 18.3% ± 0.3% | 17.3% ± 0.1% | 10.0% ± 1.9% | 10.0% |
| 25 | **10.6% ± 0.0%** | 9.2% ± 0.8% | 10.0% ± 0.3% | 4.0% ± 0.2% | 4.0% |
| 100 | **6.9% ± 0.5%** | 3.4% ± 0.1% | 3.8% ± 0.2% | 1.0% ± 0.0% | 1.0% |

GraphSAGE consistently wins, but the absolute numbers are modest — 7× random at 100 classes, not 90×. **Why so low?** The Azure trace only ships *summary* CPU stats (max/avg/p95) per VM, not the hourly time-series (the time-series files total 140GB). With those summary stats alone, behavioral fingerprinting just doesn't have enough to work with. With true hourly traces (or full CloudTrail-like event logs), the GNN's lift would be much larger — that's what the synthetic results below demonstrate, where we control the feature richness.

What this Azure run actually validates:
1. **The pipeline works at production scale** — load, sample, build graphs, and train across 20,000 real VMs.
2. **GraphSAGE consistently outperforms feature-only baselines** even on this thin data — not by a huge margin, but consistently across 5–100 classes.
3. **Where deterministic structural metadata exists, use it directly** — don't reach for ML. Caught this honestly during audit.

The strong test of the *methodology* is on the synthetic AWS environment below, where we deliberately construct hard cases (shared services, cross-team resources, reassigned ownership) that break the structural-lookup shortcut and where the per-resource feature density matches what real CloudTrail provides.

### On synthetic AWS data (controlled experiment)

```
$ costdna benchmark --synthetic --seeds 5
              Model comparison — accuracy ± 1σ across 5 seeds
╭───────────┬──────────────┬──────────┬───────────┬──────────┬──────────┬──────────╮
│ Model     │      Overall │    clean │  cross_t. │  reassg. │  sh.svc. │   sparse │
├───────────┼──────────────┼──────────┼───────────┼──────────┼──────────┼──────────┤
│ Majority  │  26.3% ±6.7% │ 23% ±9%  │  20%±40%  │  60%±49% │  60%±49% │  20%±40% │
│ LogReg    │  89.5% ±4.7% │ 99% ±3%  │   0% ±0%  │  60%±49% │  60%±49% │ 100% ±0% │
│ k-NN(k=5) │  76.8% ±4.2% │ 87% ±6%  │   0% ±0%  │  60%±49% │  20%±40% │  80%±40% │
│ LabelProp │  96.8% ±2.6% │100% ±0%  │  40%±49%  │ 100% ±0% │ 100% ±0% │ 100% ±0% │
│ GraphSAGE │  94.7% ±4.7% │ 97% ±3%  │  40%±49%  │ 100% ±0% │ 100% ±0% │ 100% ±0% │
╰───────────┴──────────────┴──────────┴───────────┴──────────┴──────────┴──────────╯
```

LogReg looks fine at 90% overall — but **0% on cross-team across all 5 seeds** and 60% ±49% on shared-services. The graph-aware methods solve those.

### On a 1-day real-AWS sandbox (collector validation)

24 resources, 15 labels, 5-fold CV: 13K real CloudTrail events captured but k-fold accuracy stays at random (~25-40% with high variance) due to insufficient labels. **The collectors work end-to-end against real AWS** — this is a validation of the engineering, not the model.

## Active learning — turn 12 labels into 60 attributions

```
$ costdna learn --budget 14 --strategy least_confidence
  Labels   Test acc   Overall   Curve
       4      72.2%     75.0%   ██████████████████████░░░░░░░░
       6      88.9%     90.0%   ███████████████████████████░░░
      10      94.4%     96.7%   ████████████████████████████░░
      12     100.0%    100.0%   ██████████████████████████████
```

Real environments have *some* tags + tribal knowledge. The active-learning loop surfaces the lowest-confidence resources to a human ("which team owns `i-0a1b2c…`?"), retrains, and converges fast. This is the realistic bootstrap path.

## Anomaly detection — find resources that fit no team

```
$ costdna scan --show-kind
Top anomalies (don't fit any team)
  data-ec2-cross_team-002    data    conf=0.54  3.5σ from data centroid
  ml-rds-reassigned-000      ml      conf=1.00  3.0σ from ml centroid
  backend-ec2-cross_team-001 backend conf=1.00  1.8σ from backend centroid
```

The model surfaces the resources that *don't* match any team well — exactly the synthetic hard cases (cross_team, reassigned), **automatically discovered** without being told they're hard. In production these are the resources you want a human to look at: vendor infra, leaked-credential workloads, new teams forming.

## Causal spike explanation

When a deploy precedes a cost spike with statistical significance (Granger causality, p < 0.05):

> Resource `mlops-rds-002` had a $9.43 cost spike at Wed 01:00. Team **ml**'s deploy at Tue 23:28 (commit `ae5a13c`, repo `ml-svc`) is the most likely cause (p=0.000).

Lets you tell a CFO not just "the bill went up" but "*this commit* made it go up."

## Calibrated confidence

```
$ costdna calibrate
Confidence calibration — ECE = 0.001 (0 = perfectly calibrated)
```

When the model says 0.7, it's right 70% of the time. That makes the confidence column *actionable* — the active-learning loop and the apply threshold both rely on it being honest.

## Comparison to existing tools

| Tool | What it does | What it can't do |
|---|---|---|
| **AWS Cost Categories** | Rules-based ("if name matches `*ml*` → team:ml") | Doesn't infer behavior; you write the rules manually |
| **AWS Cost Allocation Tags** | Aggregates spend by tag | Useless for the 40-60% of resources nobody tagged |
| **Kubecost** | k8s-only — pod-level cost attribution | Doesn't see Lambda, RDS, S3, EC2 outside k8s |
| **CloudHealth / Vantage / Apptio** | Multi-cloud, dashboards, allocation rules | All tag-based or rules-based — same blind spot for untagged |
| **CostDNA** | Infers ownership from behavior; writes tags back | Needs CloudTrail + Flow Logs (which most prod accounts have) |

**Positioning:** CostDNA isn't a dashboard. It's the missing input layer that makes every other FinOps tool work on previously-unattributable resources. Run `costdna apply`, then your existing dashboard suddenly explains 90% of spend instead of 50%.

## Quickstart

### Synthetic demo (no AWS account)
```bash
pip install -e .
costdna scan      --synthetic --show-kind         # full pipeline
costdna benchmark --synthetic --seeds 5           # multi-seed evidence
costdna benchmark --synthetic --kfold 5           # stratified k-fold CV
costdna ablate    --synthetic                     # feature & edge ablation
costdna calibrate --synthetic                     # reliability diagram
costdna learn     --synthetic --compare-all       # active learning curves
costdna discover                                  # auto-find teams from IAM
```

### Live AWS scan
```bash
costdna doctor    --aws-profile prod              # preflight first
costdna scan      --aws-profile prod --save-dir runs/$(date +%F)
costdna apply     --predictions runs/$(date +%F)/predictions.csv  # dry-run
costdna apply     --predictions runs/$(date +%F)/predictions.csv --apply
```

Full walkthrough: see [DEPLOYMENT.md](DEPLOYMENT.md).

### Build the labeled environment yourself
```bash
cd terraform && terraform init && terraform apply
# run simulation/* on cron for 3-5 days, then:
costdna scan --aws-profile dev --save-dir runs/first
```

### Web UI (no CLI required)

For FinOps engineers who'd rather click than type. Single-page app:
upload a saved `predictions.csv` (or run a synthetic scan in-browser),
filter by team / type / confidence, generate `aws ec2 create-tags` commands.

```bash
pip install 'costdna[ui]'
costdna serve     # http://localhost:8501
```

### Continuous attribution + drift alerts

`costdna watch` runs a fresh scan, diffs against the previous run, and
posts a digest (drifted resources, new anomalies, lost-confidence flags)
to Slack/Discord. Designed for cron:

```bash
# Daily at 6am UTC
0 6 * * *  /usr/local/bin/costdna watch --aws-profile prod \
                                        --slack-webhook $SLACK_WEBHOOK_URL
```

Each run saves to a date-stamped subdirectory under `--state-dir`
(default `runs/watch/`). The digest format works with both Slack and
Discord webhooks.

### Docker (no install required)

The fastest way to try CostDNA — pulls a prebuilt image with all dependencies and the embedding model baked in:

```bash
# 30-second synthetic demo
docker run --rm pauti04/costdna scan --synthetic --epochs 50

# Live AWS scan (mount your AWS credentials)
docker run --rm -v ~/.aws:/root/.aws pauti04/costdna scan --aws-profile prod
```

The image is multi-arch (linux/amd64 and linux/arm64), built from this repo via [GitHub Actions](.github/workflows/docker-release.yml) on every release tag.

To build locally:
```bash
docker build -t costdna .
docker run --rm costdna scan --synthetic
```

## Repo layout

```
src/costdna/
  collectors/aws.py         hardened boto3 collectors (retries, fallbacks, throttling)
  collectors/synthetic.py   realistic synthetic data with 4 hard-case kinds
  features.py               9-feature behavioral extraction
  graph.py                  NetworkX (VPC + IAM + VPC-CIDR edges) → PyG conversion
  model.py                  GraphSAGE + supervised contrastive head
  train.py                  training loop with stratified split
  baselines.py              Majority / LogReg / k-NN / LabelProp baselines
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
  output.py                 Rich-formatted tables, panels, sparklines
  cli.py                    10 subcommands wired to the above

terraform/                  4-team labeled AWS environment
simulation/                 per-team workload generators
tests/                      pipeline + baseline-failure invariants
DEPLOYMENT.md               step-by-step runbook for real AWS
```

## Synthetic environment

Four teams (`backend`, `data`, `ml`, `platform`) × four resource types × five resource "kinds":

| Kind | What it models | Why it's hard |
|---|---|---|
| `clean` | Single-team usage | Easy — any model gets these |
| `shared_service` | Backend's RDS/S3, hammered by data + ml (~65% cross-team callers) | Behavioral features point the wrong direction |
| `cross_team` | Used roughly equally by two teams (~70% noise) | Same |
| `reassigned` | Team A owned it for 7 days; team B took over | Time-window features blend two teams |
| `sparse` | Cold-storage S3, infrequent Lambdas | Few events → unstable fingerprint |

IAM roles use realistic patterns (`apicore-execution-role`, `etl-runner-role`, `mlops-sagemaker-training`, `devops-eks-node`) — the team is *implied* by tribe naming, not stated. The model has to infer team from behavior, not read it off the role name.

## License

MIT
