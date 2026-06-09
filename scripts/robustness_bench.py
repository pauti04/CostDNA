"""Robustness benchmark — how gracefully does attribution degrade under stress?

Two curves on the synthetic env (fixed graph + stratified split, same trainer
as benchmark.py so it's apples-to-apples):

1. LABEL NOISE: flip X% of *training* labels to a wrong class; test labels stay
   clean. Simulates wrong tribal-knowledge / stale-tag seed labels.
2. EDGE DROPOUT: randomly keep X% of graph edges. Simulates missing VPC-flow /
   IAM / throttled-CloudTrail data — an incomplete graph.

Reproduce: PYTHONPATH=src python scripts/robustness_bench.py
"""
from __future__ import annotations

import sys

import numpy as np
import torch

from costdna import TEAMS
from costdna.benchmark import _train_with_fixed_split
from costdna.collectors import generate_synthetic_signals
from costdna.features import extract_features, normalize_features
from costdna.graph import build_graph, to_pyg
from costdna.robustness import drop_edges, inject_label_noise

SEEDS = [7, 42, 123]
NOISE_LEVELS = [0.0, 0.10, 0.20, 0.30, 0.40]
EDGE_KEEP = [1.0, 0.75, 0.50, 0.25, 0.0]
N_CLASSES = len(TEAMS)


def _stratified_split(y, labeled_mask, train_frac, seed):
    rng = np.random.default_rng(seed)
    idx = np.where(labeled_mask)[0]
    train = np.zeros_like(labeled_mask)
    test = np.zeros_like(labeled_mask)
    for cls in np.unique(y[idx]):
        c = idx[y[idx] == cls]
        rng.shuffle(c)
        cut = max(1, int(len(c) * train_frac))
        train[c[:cut]] = True
        if len(c) > 1:
            test[c[cut:]] = True
    return train, test


def _build(seed):
    sig, meta, flows, _ = generate_synthetic_signals(
        n_per_type_per_team=4, days=14, seed=seed)
    feats = normalize_features(extract_features(sig, meta))
    g = build_graph(feats, meta, flows, sig)
    labels = {r["resource_id"]: TEAMS.index(r["team"])
              for _, r in meta.iterrows() if r["team"] in TEAMS}
    return to_pyg(g, labels)


def run():
    noise_curve = {lvl: [] for lvl in NOISE_LEVELS}
    edge_curve = {kf: [] for kf in EDGE_KEEP}

    for seed in SEEDS:
        data = _build(seed)
        y = data.y.cpu().numpy()
        labeled = data.labeled_mask.cpu().numpy()
        train_mask, test_mask = _stratified_split(y, labeled, 0.7, seed)
        train_idx = np.where(train_mask)[0]
        tm, te = torch.tensor(train_mask), torch.tensor(test_mask)

        # ---- Label-noise curve (clean graph) ----
        for lvl in NOISE_LEVELS:
            rng = np.random.default_rng(seed * 100 + int(lvl * 100))
            noisy_y = inject_label_noise(y, train_idx, lvl, N_CLASSES, rng)
            d = data.clone()
            d.y = torch.tensor(noisy_y)
            # test_acc is measured against the (clean) test labels inside the trainer
            d.y[test_mask] = data.y[test_mask]
            res = _train_with_fixed_split(d, N_CLASSES, tm, te, epochs=150, seed=seed)
            noise_curve[lvl].append(res.test_acc)
            print(f"  seed {seed}  noise {lvl:.0%}  test_acc={res.test_acc:.3f}",
                  file=sys.stderr)

        # ---- Edge-dropout curve (clean labels) ----
        edge_np = data.edge_index.cpu().numpy()
        for kf in EDGE_KEEP:
            rng = np.random.default_rng(seed * 1000 + int(kf * 100))
            kept = drop_edges(edge_np, kf, rng)
            d = data.clone()
            d.edge_index = torch.tensor(kept, dtype=torch.long)
            res = _train_with_fixed_split(d, N_CLASSES, tm, te, epochs=150, seed=seed)
            edge_curve[kf].append(res.test_acc)
            print(f"  seed {seed}  edges {kf:.0%}  test_acc={res.test_acc:.3f}",
                  file=sys.stderr)

    def _fmt(curve, keys, label):
        print(f"\n=== {label} (synthetic env, {len(SEEDS)} seeds) ===")
        base = float(np.mean(curve[keys[0]]))
        for k in keys:
            a = np.array(curve[k])
            m, s = a.mean(), a.std()
            delta = f"  ({(m - base) * 100:+.0f} pts vs baseline)" if k != keys[0] else "  (baseline)"
            print(f"  {label.split()[0]} {k:>5}: {m * 100:5.1f}% ± {s * 100:4.1f}%{delta}")

    _fmt(noise_curve, NOISE_LEVELS, "LABEL NOISE (train labels corrupted)")
    _fmt(edge_curve, EDGE_KEEP, "EDGE DROPOUT (graph edges kept)")


if __name__ == "__main__":
    run()
