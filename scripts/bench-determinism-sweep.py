"""Controlled experiment: label-propagation accuracy is a function of edge
determinism, not model quality.

This isolates the paper's mechanism. We build a node-classification task with
$T$ classes and inject a single graph edge whose determinism of the label we
control from 0 to 1 (nodes sharing an edge-group value are connected). We then
run label propagation --- the sharpest diagnostic, because it has no learned
parameters and no features: it simply spreads observed labels across edges.

Its test accuracy is therefore a pure readout of how much the edge encodes the
label. The expectation, which the formal proposition in the paper predicts, is
a near-linear climb from the random floor to ${\\sim}100\\%$ as the injected
edge goes from non-deterministic to deterministic. This is why a leaking edge
turns "prediction" into a lookup: at determinism 1, propagation is exact and
requires no learning at all.

Output: runs/determinism-sweep/results.json + docs/paper/fig-sweep.pdf
Reproduce:  PYTHONPATH=src python scripts/bench-determinism-sweep.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
OUT_JSON = ROOT / "runs" / "determinism-sweep" / "results.json"
OUT_FIG = ROOT / "docs" / "paper" / "fig-sweep.pdf"

SEEDS = [7, 42, 911, 1234, 2718]
LEVELS = [0.0, 0.15, 0.30, 0.50, 0.70, 0.85, 1.0]
N_NODES = 400
N_CLASSES = 5
GROUP_SIZE = 4
TRAIN_FRAC = 0.7


def _build(target_det: float, rng: np.random.Generator):
    """Return (labels, group_of_node, actual_determinism).

    A fraction ~target_det of edge-groups are 'pure' (all one class); the rest
    are 'mixed' (span classes). Group id is the injected edge value.
    """
    labels = rng.integers(0, N_CLASSES, size=N_NODES)
    by_class: dict[int, list[int]] = {}
    order = rng.permutation(N_NODES)
    for i in order:
        by_class.setdefault(int(labels[i]), []).append(int(i))

    n_groups = N_NODES // GROUP_SIZE
    n_pure = int(round(target_det * n_groups))
    group_of = np.full(N_NODES, -1, dtype=int)
    gid = 0

    classes = list(by_class.keys())
    ci = 0
    made = 0
    while made < n_pure and any(by_class[c] for c in classes):
        tries = 0
        while not by_class[classes[ci % len(classes)]] and tries < len(classes):
            ci += 1; tries += 1
        pool = by_class[classes[ci % len(classes)]]
        if not pool:
            break
        for _ in range(min(GROUP_SIZE, len(pool))):
            group_of[pool.pop()] = gid
        gid += 1; made += 1; ci += 1

    # Remaining -> mixed groups: round-robin across classes to force mixing.
    rem: list[int] = []
    pools = [by_class[c] for c in classes if by_class[c]]
    while pools:
        for p in pools:
            if p:
                rem.append(p.pop())
        pools = [p for p in pools if p]
    for j in range(0, len(rem), GROUP_SIZE):
        for node in rem[j:j + GROUP_SIZE]:
            group_of[node] = gid
        gid += 1

    # actual determinism = fraction of groups mapping to exactly one class
    groups: dict[int, set] = {}
    for node in range(N_NODES):
        groups.setdefault(int(group_of[node]), set()).add(int(labels[node]))
    actual_det = np.mean([len(s) == 1 for s in groups.values()])
    return labels, group_of, float(actual_det)


def _label_prop_accuracy(labels, group_of, rng):
    """1-step label propagation on the injected graph: each test node is
    predicted as the majority label among its labeled group-mates (its graph
    neighbors); global-majority fallback if it has none."""
    train_mask = rng.random(N_NODES) < TRAIN_FRAC
    global_majority = Counter(labels[train_mask]).most_common(1)[0][0]
    members: dict[int, list[int]] = {}
    for node in range(N_NODES):
        members.setdefault(int(group_of[node]), []).append(node)

    correct = total = 0
    for node in range(N_NODES):
        if train_mask[node]:
            continue
        total += 1
        neigh = [m for m in members[int(group_of[node])] if m != node and train_mask[m]]
        if neigh:
            pred = Counter(labels[m] for m in neigh).most_common(1)[0][0]
        else:
            pred = global_majority
        correct += int(pred == labels[node])
    return correct / max(1, total)


def main():
    results = {"seeds": SEEDS, "levels": [], "random": 1.0 / N_CLASSES,
               "n_nodes": N_NODES, "n_classes": N_CLASSES, "group_size": GROUP_SIZE}
    for lv in LEVELS:
        dets, accs = [], []
        for seed in SEEDS:
            rng = np.random.default_rng(seed)
            labels, group_of, det = _build(lv, rng)
            accs.append(_label_prop_accuracy(labels, group_of, rng))
            dets.append(det)
        entry = {"nominal": lv, "actual_det": float(np.mean(dets)),
                 "labelprop_mean": float(np.mean(accs)),
                 "labelprop_std": float(np.std(accs))}
        results["levels"].append(entry)
        print(f"  det≈{entry['actual_det']:.2f}: LabelProp={entry['labelprop_mean']:.1%} "
              f"± {entry['labelprop_std']:.1%}", file=sys.stderr)

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(results, indent=2) + "\n")
    print(f"Wrote {OUT_JSON.relative_to(ROOT)}", file=sys.stderr)
    _plot(results)


def _plot(results):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    lv = results["levels"]
    x = [e["actual_det"] for e in lv]
    y = [e["labelprop_mean"] * 100 for e in lv]
    ye = [e["labelprop_std"] * 100 for e in lv]
    rnd = results["random"] * 100

    fig, ax = plt.subplots(figsize=(5.0, 3.3))
    # Proposition: for a well-covered graph, accuracy ~= determinism (identity).
    ax.plot([0, 1], [0, 100], ls=":", color="#888", lw=1.2,
            label="proposition: acc $\\approx$ determinism")
    ax.errorbar(x, y, yerr=ye, marker="o", capsize=3, color="#c0392b",
                label="label propagation (empirical)")
    ax.axhline(rnd, ls="--", color="gray", lw=1, label=f"random ({rnd:.0f}%)")
    ax.set_xlabel("Determinism of the injected edge w.r.t. the label")
    ax.set_ylabel("Test accuracy (%)")
    ax.set_ylim(0, 100); ax.set_xlim(-0.02, 1.02)
    ax.legend(fontsize=8, loc="upper left", frameon=False)
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    OUT_FIG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_FIG, bbox_inches="tight")
    print(f"Wrote {OUT_FIG.relative_to(ROOT)}", file=sys.stderr)


if __name__ == "__main__":
    main()
