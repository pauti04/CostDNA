"""Benchmark on Microsoft's published Philly DL-cluster trace (post-audit).

Mirrors scripts/bench-azure.py for the second dataset in the leakage thesis.
The Philly collector maps:
  - iam_role  <- job's `user`            (the LEAKING edge: user -> vc)
  - vpc_cidr  <- job's `primary_machine` (honest: machines shared across VCs)

So de-leaking Philly = drop the user/iam edge and keep only the machine
edge. This script:

1. Loads the trace (top-N virtual clusters).
2. Runs find_deterministic_edges to MEASURE how deterministic user->vc and
   machine->vc actually are (verifies/《corrects》 the "0.85" claim).
3. Runs the baseline sweep TWICE per N:
     - "leaky":     edge_kinds=("iam","vpc")  — includes the user edge
     - "de-leaked": edge_kinds=("vpc",)       — machine edge only
   over multiple seeds, so the honest before/after drop is real, not prose.

Output: runs/philly-honest/results.json + a printed summary.

Reproduce:  PYTHONPATH=src python scripts/bench-philly.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

from costdna.audit import find_deterministic_edges
from costdna.benchmark import aggregate_seeds, run_benchmark
from costdna.collectors.philly import load_philly_trace
from costdna.features import extract_features, normalize_features
from costdna.graph import build_graph, to_pyg

ROOT = Path(__file__).resolve().parent.parent
JOB_LOG = ROOT / "data" / "philly" / "trace-data" / "cluster_job_log"
OUT = ROOT / "runs" / "philly-honest" / "results.json"

SEEDS = [7, 42, 911]
N_VCS = [3, 5, 10, 15]
MAX_JOBS_PER_VC = 200


def _subset_and_build(signals, metadata, flows, n_vcs, seed, edge_kinds):
    rng = np.random.default_rng(seed)
    all_vcs = sorted(metadata["team"].unique())
    chosen = sorted(rng.choice(all_vcs, size=min(n_vcs, len(all_vcs)),
                               replace=False))
    idx = {t: i for i, t in enumerate(chosen)}
    md = metadata[metadata["team"].isin(chosen)].reset_index(drop=True)
    sig = signals[signals["resource_id"].isin(md["resource_id"])]

    feats = extract_features(sig, md)
    feats_norm = normalize_features(feats)
    g = build_graph(feats_norm, md, flows, sig, edge_kinds=edge_kinds)
    labels = {row["resource_id"]: idx[row["team"]] for _, row in md.iterrows()}
    data = to_pyg(g, labels)
    kinds = ["clean"] * len(md)
    return data, g, feats_norm.values, kinds, len(chosen)


def _run(signals, metadata, flows, n_vcs, edge_kinds):
    per_seed = []
    for seed in SEEDS:
        data, g, feats_arr, kinds, actual_n = _subset_and_build(
            signals, metadata, flows, n_vcs, seed, edge_kinds)
        rows, _ = run_benchmark(data, g, feats_arr, kinds,
                                n_classes=actual_n, seed=seed,
                                epochs=80, train_frac=0.7)
        per_seed.append(rows)
    return {r.name: (round(r.test_acc_mean, 4), round(r.test_acc_std, 4))
            for r in aggregate_seeds(per_seed, SEEDS)}


def main():
    print(f"Loading {JOB_LOG} …", file=sys.stderr)
    signals, metadata, flows, _ = load_philly_trace(
        JOB_LOG, top_n_vcs=max(N_VCS), max_jobs_per_vc=MAX_JOBS_PER_VC, seed=42)
    print(f"  {len(metadata)} jobs across {metadata['team'].nunique()} VCs",
          file=sys.stderr)

    # ---- Audit: how deterministic are the candidate edges of the label? ----
    det = find_deterministic_edges(
        metadata, target_col="team",
        candidate_edge_cols=["iam_role", "vpc_cidr", "resource_type"],
        threshold=0.0,  # report all, don't filter
    )
    print("\n=== EDGE AUDIT (determinism of team) ===", file=sys.stderr)
    for col, d in det.items():
        tag = {"iam_role": "user  (LEAK candidate)",
               "vpc_cidr": "machine (honest candidate)"}.get(col, col)
        print(f"  {tag:<28} {d:.3f}", file=sys.stderr)

    results = {"seeds": SEEDS, "audit": det, "leaky": {}, "deleaked": {}}

    for n in N_VCS:
        print(f"\n=== N = {n} VCs ===", file=sys.stderr)
        t0 = time.time()
        leaky = _run(signals, metadata, flows, n, ("iam", "vpc"))
        deleaked = _run(signals, metadata, flows, n, ("vpc",))
        results["leaky"][n] = leaky
        results["deleaked"][n] = deleaked
        gl = leaky.get("GraphSAGE", (0, 0))[0]
        gd = deleaked.get("GraphSAGE", (0, 0))[0]
        print(f"  GraphSAGE  leaky={gl:.1%}  de-leaked={gd:.1%}  "
              f"(random={1/n:.1%})  [{time.time()-t0:.0f}s]", file=sys.stderr)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, indent=2) + "\n")
    print(f"\nWrote {OUT.relative_to(ROOT)}", file=sys.stderr)

    # Headline for the docs.
    g15_leak = results["leaky"][15]["GraphSAGE"][0]
    g15_honest = results["deleaked"][15]["GraphSAGE"][0]
    print(f"\nHEADLINE (15 VCs): GraphSAGE {g15_leak:.0%} (leaky) "
          f"-> {g15_honest:.0%} (de-leaked), random={1/15:.1%}, "
          f"ratio={g15_honest*15:.1f}x", file=sys.stderr)


if __name__ == "__main__":
    main()
