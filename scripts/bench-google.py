"""Benchmark on Google's Borg cluster trace (post-audit). Third dataset,
third vendor, non-Microsoft.

The Borg trace has no "team," but it has the same structural-leak shape. We
pose a node-classification task: predict an instance's *scheduling priority*
(5 tiers) from its resource-request behavior. The audit finds that
`collection_id` (the job/service an instance belongs to) is ~99.8%
deterministic of priority — every instance in a service shares a priority
tier — so a graph edge on `collection_id` is a near-perfect lookup, exactly
like Azure's `deployment_id -> subscription`.

Mapping into CostDNA's schema (same trick as bench-philly.py):
  metadata.team     <- priority          (the 5-class target)
  metadata.vpc_cidr <- collection_id      (the leaking structural edge)
  signals(cost)     <- cpu / memory request (the honest behavioral features)

We compare:
  leaky      : edge_kinds=("vpc",)   -> collection_id edges present
  de-leaked  : edge_kinds=()          -> no structural edge; features only

Output: runs/google-honest/results.json + printed summary.
Reproduce:  PYTHONPATH=src python scripts/bench-google.py
"""
from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from costdna.audit import find_deterministic_edges
from costdna.benchmark import aggregate_seeds, run_benchmark
from costdna.features import extract_features, normalize_features
from costdna.graph import build_graph, to_pyg

ROOT = Path(__file__).resolve().parent.parent
EVENTS = ROOT / "data" / "google" / "instance_events_part0.json.gz"
OUT = ROOT / "runs" / "google-honest" / "results.json"

SEEDS = [7, 42, 911]
MAX_PER_PRIORITY = 400          # balance the 5 priority tiers
MAX_LINES = 400_000


def _load() -> pd.DataFrame:
    recs = []
    seen = set()
    with gzip.open(EVENTS, "rt") as f:
        for i, line in enumerate(f):
            if i >= MAX_LINES:
                break
            try:
                r = json.loads(line)
            except Exception:
                continue
            cid, idx = r.get("collection_id"), r.get("instance_index")
            pr = r.get("priority")
            rr = r.get("resource_request") or {}
            cpu, mem = rr.get("cpus"), rr.get("memory")
            if cid is None or pr is None or cpu is None or mem is None:
                continue
            key = (cid, idx)
            if key in seen:
                continue
            seen.add(key)
            recs.append((f"{cid}-{idx}", str(cid), str(r.get("machine_id")),
                         str(pr), float(cpu), float(mem)))
    df = pd.DataFrame(recs, columns=[
        "resource_id", "collection_id", "machine_id", "priority", "cpus", "memory"])
    # Balance priority tiers so Majority isn't trivially high.
    parts = []
    for _pr, g in df.groupby("priority"):
        parts.append(g.sample(min(len(g), MAX_PER_PRIORITY), random_state=0))
    return pd.concat(parts, ignore_index=True)


def _to_costdna(df: pd.DataFrame):
    metadata = pd.DataFrame({
        "resource_id": df["resource_id"],
        "resource_type": "instance",
        "team": df["priority"],                 # target = priority tier
        "kind": "clean",
        "iam_role": df["machine_id"],
        "vpc_cidr": df["collection_id"],         # leaking structural edge
        "created_at": "",
    })
    # Behavioral features as cost signals (cpu and memory request).
    rows = []
    anchor = "2019-05-01T00:00:00+00:00"
    for _, r in df.iterrows():
        rows.append({"resource_id": r["resource_id"], "signal_type": "cost",
                     "value": r["cpus"] * 100.0, "timestamp": anchor})
        rows.append({"resource_id": r["resource_id"], "signal_type": "cost",
                     "value": r["memory"] * 100.0, "timestamp": anchor})
    signals = pd.DataFrame(rows)
    signals["timestamp"] = pd.to_datetime(signals["timestamp"], utc=True)
    return metadata, signals


def _run(metadata, signals, edge_kinds, teams):
    idx = {t: i for i, t in enumerate(teams)}
    per_seed = []
    for seed in SEEDS:
        feats = extract_features(signals, metadata)
        feats_norm = normalize_features(feats)
        g = build_graph(feats_norm, metadata, pd.DataFrame(), signals,
                        edge_kinds=edge_kinds)
        labels = {r["resource_id"]: idx[r["team"]] for _, r in metadata.iterrows()}
        data = to_pyg(g, labels)
        kinds = ["clean"] * len(metadata)
        rows, _ = run_benchmark(data, g, feats_norm.values, kinds,
                                n_classes=len(teams), seed=seed,
                                epochs=80, train_frac=0.7)
        per_seed.append(rows)
    return {r.name: (round(r.test_acc_mean, 4), round(r.test_acc_std, 4))
            for r in aggregate_seeds(per_seed, SEEDS)}


def main():
    print(f"Loading {EVENTS} …", file=sys.stderr)
    df = _load()
    teams = sorted(df["priority"].unique())
    print(f"  {len(df)} instances, priority tiers={teams}", file=sys.stderr)

    det = find_deterministic_edges(
        df.rename(columns={"priority": "team"}), "team",
        ["collection_id", "machine_id"], threshold=0.0)
    print("  EDGE AUDIT (determinism of priority):", file=sys.stderr)
    for k, v in det.items():
        print(f"    {k:<16} {v:.3f}", file=sys.stderr)

    metadata, signals = _to_costdna(df)
    print("  running leaky (collection_id edge) …", file=sys.stderr)
    leaky = _run(metadata, signals, ("vpc",), teams)
    print("  running de-leaked (features only, no structural edge) …", file=sys.stderr)
    deleaked = _run(metadata, signals, (), teams)

    results = {"seeds": SEEDS, "n_classes": len(teams), "random": 1.0 / len(teams),
               "audit": det, "leaky": leaky, "deleaked": deleaked}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, indent=2) + "\n")

    gl = leaky["GraphSAGE"][0]; gd = deleaked["GraphSAGE"][0]
    print(f"\nHEADLINE: GraphSAGE {gl:.1%} (leaky, collection_id edge) -> "
          f"{gd:.1%} (de-leaked), random={1/len(teams):.1%}", file=sys.stderr)
    print(f"Wrote {OUT.relative_to(ROOT)}", file=sys.stderr)


if __name__ == "__main__":
    main()
