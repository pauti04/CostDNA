# Changelog

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
