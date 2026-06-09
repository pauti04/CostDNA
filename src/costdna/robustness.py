"""Robustness perturbations — stress-test attribution under realistic data problems.

Two failure modes that any real deployment hits:

1. **Label noise.** Ground-truth team labels come from tribal knowledge and
   stale tags — they're wrong some of the time. A usable model has to degrade
   gracefully as the seed labels get noisier, not collapse.

2. **Incomplete graph.** Real accounts are missing VPC flow logs, have partial
   IAM visibility, or throttle CloudTrail. The graph the model trains on is a
   subsample of the true one. How much does accuracy depend on the graph being
   complete?

These functions are pure and deterministic (seeded) so the degradation curves
in `scripts/robustness_bench.py` are reproducible. They don't depend on torch
— they operate on numpy label arrays and edge-index arrays — so they're cheap
to unit-test.
"""

from __future__ import annotations

import numpy as np

__all__ = ["inject_label_noise", "drop_edges"]


def inject_label_noise(
    y: np.ndarray,
    indices: np.ndarray,
    frac: float,
    n_classes: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Flip a fraction of the labels at `indices` to a uniformly-random WRONG class.

    Returns a copy; the input is not mutated. Only the positions in `indices`
    are eligible to flip — in the robustness harness those are the *training*
    labels, so the held-out test labels stay clean and the measured accuracy
    is honest.

    Parameters
    ----------
    y : np.ndarray
        Integer class labels, shape (n_nodes,).
    indices : np.ndarray
        Positions eligible for corruption (typically the train split).
    frac : float
        Fraction of `indices` to corrupt, in [0, 1].
    n_classes : int
        Number of classes; flips are drawn from the other n_classes-1.
    rng : np.random.Generator
        Seeded generator for reproducibility.
    """
    if not 0.0 <= frac <= 1.0:
        raise ValueError(f"frac must be in [0, 1], got {frac}")
    out = y.copy()
    idx = np.asarray(indices)
    n_flip = int(round(len(idx) * frac))
    if n_flip == 0:
        return out
    chosen = rng.choice(idx, size=n_flip, replace=False)
    for i in chosen:
        # Draw a wrong class: pick from 0..n_classes-2, then skip over the
        # true label so the result is guaranteed different.
        wrong = int(rng.integers(0, n_classes - 1))
        if wrong >= out[i]:
            wrong += 1
        out[i] = wrong
    return out


def drop_edges(
    edge_index: np.ndarray,
    keep_frac: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """Randomly keep `keep_frac` of the graph's edges (simulating incomplete data).

    `edge_index` is the PyG-style (2, E) array. Returns a (2, E') view with
    E' = round(E * keep_frac) columns. keep_frac=1.0 returns all edges;
    keep_frac=0.0 returns an empty (2, 0) graph (the model degrades to a
    feature-only MLP, which is exactly the "no graph signal" floor).

    Edges are kept as-is (we don't symmetrize) — the harness passes an
    already-undirected edge_index, so dropping a column drops one direction;
    over many edges this approximates uniform edge removal, which is the
    realistic "missing flow-log / IAM record" failure mode.
    """
    if not 0.0 <= keep_frac <= 1.0:
        raise ValueError(f"keep_frac must be in [0, 1], got {keep_frac}")
    e = np.asarray(edge_index)
    total = e.shape[1]
    n_keep = int(round(total * keep_frac))
    if n_keep >= total:
        return e
    if n_keep == 0:
        return e[:, :0]
    keep = rng.choice(total, size=n_keep, replace=False)
    keep.sort()
    return e[:, keep]
