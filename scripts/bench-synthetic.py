"""Phase 2 benchmark — generates the primary results table for the new README.

Runs the full baseline suite (Majority, LogReg, k-NN, LabelProp, node2vec+LR,
GraphSAGE) on the synthetic env across 5 seeds, reports mean ± std overall and
per-kind.

This is the table that goes into docs/v2/results-phase2.md and (via Phase 1)
into the new README section 03.
"""
from __future__ import annotations

import json
import sys
import time

from costdna import TEAMS
from costdna.benchmark import run_benchmark_multiseed
from costdna.collectors import generate_synthetic_signals
from costdna.features import extract_features, normalize_features
from costdna.graph import build_graph, to_pyg


def build_data(seed: int):
    signals, metadata, flows, _ = generate_synthetic_signals(
        n_per_type_per_team=3, days=14, seed=seed,
    )
    metadata = metadata[metadata["team"].isin(TEAMS)].reset_index(drop=True)
    signals = signals[signals["resource_id"].isin(metadata["resource_id"])]
    feats_norm = normalize_features(extract_features(signals, metadata))
    g = build_graph(feats_norm, metadata, flows, signals)
    labels = {row["resource_id"]: TEAMS.index(row["team"])
              for _, row in metadata.iterrows()}
    data = to_pyg(g, labels)
    kinds = list(metadata["kind"])
    return data, g, feats_norm.values, kinds


SEEDS = [7, 42, 123, 256, 911]
print(f"Running multi-seed benchmark across {len(SEEDS)} seeds: {SEEDS}", file=sys.stderr)
t0 = time.time()
rows = run_benchmark_multiseed(build_data, seeds=SEEDS, train_frac=0.7, epochs=100)
elapsed = time.time() - t0
print(f"Done in {elapsed:.1f}s", file=sys.stderr)

# Print results in machine-readable form first
print("\n=== JSON-shaped output for results doc ===")
out = []
for r in rows:
    out.append({
        "model": r.name,
        "overall_mean": round(r.test_acc_mean, 4),
        "overall_std": round(r.test_acc_std, 4),
        "per_kind_mean": {k: round(v, 4) for k, v in r.per_kind_mean.items()},
        "per_kind_std": {k: round(v, 4) for k, v in r.per_kind_std.items()},
    })
print(json.dumps(out, indent=2))

# Then human-readable table
print("\n=== Markdown table (overall) ===")
print("| Model        | Overall        |")
print("|--------------|----------------|")
for r in rows:
    print(f"| {r.name:<12} | {r.test_acc_mean:.3f} ± {r.test_acc_std:.3f}  |")

print("\n=== Markdown table (per-kind) ===")
kinds = sorted({k for r in rows for k in r.per_kind_mean})
header = "| Model        | " + " | ".join(f"{k:<14}" for k in kinds) + " |"
sep    = "|--------------|" + "|".join("-" * 16 for _ in kinds) + "|"
print(header)
print(sep)
for r in rows:
    cells = []
    for k in kinds:
        m = r.per_kind_mean.get(k)
        s = r.per_kind_std.get(k)
        if m is None:
            cells.append(f"{'—':<14}")
        else:
            cells.append(f"{m:.2f} ± {s:.2f}".ljust(14))
    print(f"| {r.name:<12} | " + " | ".join(cells) + " |")
