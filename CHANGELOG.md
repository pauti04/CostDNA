# Changelog

## [0.3.0] — 2026-05-09

Major release. 54 commits since v0.1.0. Project went from "research artifact"
to "shippable product" — live demo, multi-cloud architecture, real-AWS
validation, drop-CSV in-browser path.

### Highlights

- **🌐 Live demo** at [cost-dna.vercel.app](https://cost-dna.vercel.app)
  with streaming responses, GPT-4o, no signup
- **🪣 Drop-your-CSV path** at [/your-account](https://cost-dna.vercel.app/your-account)
  — visitors analyse their own AWS bill in-browser, nothing transmitted
- **☁️ Multi-cloud architecture** — AWS production-tested (87% on a real
  account), Azure + GCP collectors implemented per official SDK patterns,
  10 mocked-shape tests
- **🧪 Real-AWS deployment**: 13/15 = 87% per-resource accuracy on a
  labelled Terraform-provisioned account; all 13 high-confidence
  predictions correct (100%)

### Added

- New tool: `find_abandoned` — surface resources whose activity has
  collapsed in the recent half of the window. 10 tools total now.
- Streaming responses in the live demo (NDJSON over ReadableStream).
- `CloudProvider` interface + Azure live (`azure_live.py`) + GCP
  (`gcp.py`) collectors; CLI `--cloud aws|azure|gcp` flag.
- Optional install extras: `pip install 'costdna[azure]'` and `'[gcp]'`.
- 8 new behavioural features (`event_diversity`, `write_ratio`,
  `events_per_active_hour`, plus per-prefix shares `describe_share` /
  `list_share` / `get_share` / `put_share` / `invoke_share`).
- GAT layer as opt-in via `GraphSAGEClassifier(conv_type="gat")`.
- Auto-shrink for small-data regimes (<30 labels): 2 layers / hidden=8 /
  dropout=0.4.
- Early stopping + stratified train/test split + class-weighted loss.
- `scripts/real-aws-test.sh` + `scripts/real-aws-finish.sh` wrapping the
  real-AWS test in two commands.
- 24/7 EC2 simulator (`terraform/simulator.tf`) with a systemd auto-pull
  timer.
- 1200×630 OG / Twitter card and proper meta tags.
- PostHog instrumentation (gated behind env var, no-op without).
- 27 vitest tests covering all 10 agent tools + the CUR analyzer.
- 10 pytest tests covering the multi-cloud collectors with mocked SDK
  shapes.

### Changed

- Site redesigned to strict white + grey palette, 10 sections,
  alternating section backgrounds, big-number callouts.
- Original 4-layer / hidden=16 GraphSAGE config preserved as default for
  the synthetic env, but auto-shrinks for small label sets — same data
  produces 53% → 87% k-fold by fixing this.
- Per-team workloads rewritten for balanced volumes and reliably-logged
  ops (object-level S3 instead of bucket-level `list_objects_v2`).
- `tests/test_pipeline.py` hard-kinds list expanded to include `sparse`
  (the new behavioural features made the previous hard kinds too easy
  for LogReg).

### Fixed

- Azure cost query was passing a raw dict; SDK v4 rejects it. Now uses
  typed `QueryDefinition` / `QueryDataset` / `QueryAggregation` /
  `QueryGrouping` / `QueryTimePeriod` objects.
- Azure `resources.list()` returns `GenericResource` without
  `created_time` — must pass `expand="createdTime,changedTime"` to get
  `GenericResourceExpanded`. Caught via SDK introspection.
- GCP Cloud Audit Log entries are `ProtobufEntry` with `payload` as a
  proto message, not a dict; previous code would have crashed with
  `AttributeError` on first contact.
- Vercel "stale alias" issue documented + scripted re-alias workflow.

### Tested + rejected

Documented in commits — these did not improve real-AWS k-fold, kept the
SAGE / 17-feature config:

- Resource-type one-hot encoding (-14%)
- Behavioral role embedding (-7% to -20%)
- 5-model softmax ensemble (-14%)
- IAM-edge filter at 50% / 80% threshold (-14%)
- GAT default for small data (collapsed to random)
- Input-feature dropout (-7%)

### Stats

- 42 tests passing across the project (15 Python + 27 TypeScript)
- CI green on tests / lint / docker / web-tests / pages
- 0 incremental AWS spend during real-AWS validation (free tier + credits)

---

## [0.2.0] — 2026-05-05

- Removed the Alibaba Cluster Trace loader and all references. Project now
  validates exclusively on Azure + Microsoft Philly + a controlled synthetic env
  + a live AWS account.
- Updated README, website, and KPIs to reflect the audit-driven narrative
  (caught two label-leakage bugs across two real datasets).

## [0.1.0] — 2026-05-05

Initial public release.

### What CostDNA does

A CLI tool that infers AWS team ownership from behavioral fingerprints
(IAM access patterns, VPC traffic, deploy timing, cost time-series shape)
using a 4-layer GraphSAGE GNN, then writes the inferred tags back to AWS
so existing FinOps tooling works on previously-unattributable spend.

### Validated on

- **Synthetic AWS environment** — 4 teams × 4 resource types × 5 hard-case
  kinds (clean, shared services, cross-team, reassigned, sparse) plus 4
  unowned categories (vendor / legacy / orphan / shadow). GNN hits 95%+ at
  controlled feature density.
- **Microsoft Azure Public Dataset V2** — 2.6M VMs, 100 subscriptions.
  Caught a label-leakage bug: `deployment_id` is 100% deterministic of
  `subscription_id`, so first-cut "97% LabelProp" was a graph database join.
  Honest behavioral-only result: GraphSAGE 6.9% (12× random) at 100 classes.
- **Microsoft Philly DL Trace** — 117K DL training jobs across 15 virtual
  clusters. `user_id` is 85% deterministic of `vc`, so user-IAM edges
  encode most of the team signal. With those edges removed, GraphSAGE
  drops to 14% (still 2× random).
- **Alibaba Cluster Trace 2018** — 71K containers across 9,790 apps.
  Audit-clean: 99.7% of machines run multiple apps. **GraphSAGE 91% on
  5 apps, 60.8% on 100 apps (61× random)**. The strongest legitimate
  real-world result.
- **Live AWS account** — Terraform-provisioned 4-team env with CloudTrail
  data events + VPC Flow Logs. Identified and fixed 7 production-grade
  boto3 bugs surfaced only by real-account testing (CloudTrail throttling,
  Cost Explorer hourly granularity opt-in, AssumeRole-from-root, etc.).

### Methodological finding

Across three real public cloud datasets, structural metadata dominates
attribution. Behavioral fingerprinting matters specifically when metadata
is missing or unreliable, which is exactly what the synthetic env's
hard-case kinds reproduce.

### CLI commands (14)

Operational: `scan`, `apply`, `diff`, `doctor`, `discover`.
Research: `benchmark`, `ablate`, `calibrate`, `learn`.
Utility: `inspect`, plus a synthetic generator and loaders for AWS,
Azure, Alibaba, and Philly datasets.

### Stack

Python 3.11 · PyTorch 2.x + PyTorch Geometric · pandas · numpy · scikit-learn
· statsmodels · networkx · boto3 · click · rich · UMAP · matplotlib ·
pytest · GitHub Actions CI · Terraform.
