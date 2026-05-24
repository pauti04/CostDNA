# Azure post-audit benchmark — second leak caught in real time

Re-ran the Azure trace benchmark on the locally-staged 2.6M-VM subsample at `runs/azure-1/` (2000 VMs across 10 subscriptions).

## Second leak finding (vpc_cidr ≡ subscription_id)

First pass used the default `edge_kinds=('iam', 'vpc')`. LabelProp immediately scored 98% — the same red flag that the original audit caught with `deployment_id`. Running the audit module on the metadata before training:

```python
>>> from costdna.audit import find_deterministic_edges
>>> find_deterministic_edges(metadata, target_col='team',
...     candidate_edge_cols=['resource_type', 'kind', 'iam_role',
...                          'vpc_cidr', 'created_at'])
{'vpc_cidr': 1.0, 'created_at': 0.8815545959284392}
```

**A second leak:** every VM in a given VPC belongs to exactly one subscription on this dataset. Using `vpc_cidr` as a graph edge reproduces the same tautology that inflated the deployment_id case. `created_at` is also partially deterministic at 88% (batch-provisioned VMs share timestamps).

**This is a real-time demonstration of the audit method working.** Without the check, the second-leak result (98% LabelProp on VPC edges) would have been the headline. With the check, we excluded the leaking edge and re-ran on the honest signal.

## Honest test accuracy — VPC edges excluded

Seeds: [7, 42, 911] · 70/30 stratified split · 80 epochs. Graph edges are IAM-role only; the Azure trace has no flow logs, so the graph is effectively empty and GraphSAGE degrades toward feature-only message passing.

| N teams | Random | Majority | LogReg | k-NN(k=5) | LabelProp | node2vec+LR | GraphSAGE |
|---|---|---|---|---|---|---|---|
| 5 | 20.0% | 17.7% ± 0.5% | 33.3% ± 1.9% | 31.2% ± 3.2% | 19.1% ± 0.4% | 33.3% ± 1.9% | 38.0% ± 3.3% |
| 10 | 10.0% | 8.7% ± 0.4% | 17.3% ± 1.4% | 16.2% ± 1.3% | 9.2% ± 0.6% | 17.3% ± 1.4% | 20.7% ± 1.0% |

**Reading the table:** all numbers should be honestly modest (single-digit-to-mid-teens on 100-class problems) because the Azure trace ships only summary CPU statistics per VM, not the hourly time-series the GNN would benefit from. The signal is whether GraphSAGE + node2vec consistently beat feature-only baselines (LogReg, k-NN) and pure-graph baselines (LabelProp).

## Reproducibility

```bash
PYTHONPATH=src python scripts/bench-azure.py
```

Replaces the `pending` cells in README §'Primary results — Azure, post-audit'. Closes GitHub issue #1.
