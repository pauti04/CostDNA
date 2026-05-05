"""Baselines we benchmark the GNN against.

The GNN is the headline architecture but if a logistic regression on raw
features gets 90% accuracy, the GNN isn't earning its complexity. These
baselines + the ablation in benchmark.py make that explicit.
"""

from __future__ import annotations

from dataclasses import dataclass

import networkx as nx
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.neighbors import KNeighborsClassifier


@dataclass
class BaselineResult:
    name: str
    train_acc: float
    test_acc: float
    predictions: np.ndarray
    confidences: np.ndarray
    per_kind: dict[str, float]   # accuracy per resource kind (clean / shared_service / etc.)


def _per_kind_accuracy(pred: np.ndarray, y: np.ndarray, kinds: list[str],
                       test_mask: np.ndarray) -> dict[str, float]:
    out: dict[str, float] = {}
    for kind in set(kinds):
        idx = np.array([i for i, k in enumerate(kinds)
                        if k == kind and test_mask[i] and y[i] >= 0])
        if len(idx) == 0:
            continue
        out[kind] = float((pred[idx] == y[idx]).mean())
    return out


def run_logistic_regression(
    features: np.ndarray, labels: np.ndarray,
    train_mask: np.ndarray, test_mask: np.ndarray,
    kinds: list[str],
) -> BaselineResult:
    clf = LogisticRegression(max_iter=2000, class_weight="balanced", C=1.0)
    clf.fit(features[train_mask], labels[train_mask])
    pred = clf.predict(features)
    conf = clf.predict_proba(features).max(axis=1)
    return BaselineResult(
        name="LogReg",
        train_acc=float(accuracy_score(labels[train_mask], pred[train_mask])),
        test_acc=float(accuracy_score(labels[test_mask], pred[test_mask])),
        predictions=pred, confidences=conf,
        per_kind=_per_kind_accuracy(pred, labels, kinds, test_mask),
    )


def run_knn(
    features: np.ndarray, labels: np.ndarray,
    train_mask: np.ndarray, test_mask: np.ndarray,
    kinds: list[str], k: int = 5,
) -> BaselineResult:
    k_eff = min(k, train_mask.sum())
    clf = KNeighborsClassifier(n_neighbors=max(1, k_eff))
    clf.fit(features[train_mask], labels[train_mask])
    pred = clf.predict(features)
    conf = clf.predict_proba(features).max(axis=1)
    return BaselineResult(
        name=f"k-NN(k={k_eff})",
        train_acc=float(accuracy_score(labels[train_mask], pred[train_mask])),
        test_acc=float(accuracy_score(labels[test_mask], pred[test_mask])),
        predictions=pred, confidences=conf,
        per_kind=_per_kind_accuracy(pred, labels, kinds, test_mask),
    )


def run_label_propagation(
    graph: nx.Graph, node_ids: list[str], labels: np.ndarray,
    train_mask: np.ndarray, test_mask: np.ndarray,
    kinds: list[str], n_classes: int,
    n_iter: int = 50,
) -> BaselineResult:
    """Pure structural baseline: harmonic label propagation on the graph.

    No features — only edge weights. If this beats the feature-only baselines
    (LogReg/k-NN), the graph carries most of the signal. If it loses, features
    do. Either way the comparison tells us where the GNN's lift comes from.
    """
    idx = {n: i for i, n in enumerate(node_ids)}
    n = len(node_ids)
    A = np.zeros((n, n))
    for u, v, data in graph.edges(data=True):
        i, j = idx[u], idx[v]
        w = float(data.get("weight", 1.0))
        A[i, j] += w
        A[j, i] += w

    # Row-normalize so each row is a transition distribution.
    row_sum = A.sum(axis=1, keepdims=True)
    row_sum[row_sum == 0] = 1.0
    P = A / row_sum

    # Initialize: one-hot for labeled nodes, uniform for unlabeled.
    Y = np.full((n, n_classes), 1.0 / n_classes)
    Y[train_mask] = 0.0
    Y[train_mask, labels[train_mask]] = 1.0

    for _ in range(n_iter):
        Y = P @ Y
        # Clamp labeled rows back to one-hot — this is what makes it "harmonic".
        Y[train_mask] = 0.0
        Y[train_mask, labels[train_mask]] = 1.0

    # Any node that ended up all-zero (disconnected, no signal) → uniform.
    zero_rows = Y.sum(axis=1) == 0
    Y[zero_rows] = 1.0 / n_classes

    pred = Y.argmax(axis=1)
    conf = Y.max(axis=1) / (Y.sum(axis=1) + 1e-9)

    return BaselineResult(
        name="LabelProp",
        train_acc=float(accuracy_score(labels[train_mask], pred[train_mask])),
        test_acc=float(accuracy_score(labels[test_mask], pred[test_mask])),
        predictions=pred, confidences=conf,
        per_kind=_per_kind_accuracy(pred, labels, kinds, test_mask),
    )


def majority_baseline(
    labels: np.ndarray, train_mask: np.ndarray, test_mask: np.ndarray,
    kinds: list[str], n_classes: int,
) -> BaselineResult:
    """The dumbest possible model — always predict the most common training label."""
    majority = int(np.bincount(labels[train_mask]).argmax())
    pred = np.full_like(labels, majority)
    conf = np.full(len(labels), 1.0 / n_classes)
    return BaselineResult(
        name="Majority",
        train_acc=float(accuracy_score(labels[train_mask], pred[train_mask])),
        test_acc=float(accuracy_score(labels[test_mask], pred[test_mask])),
        predictions=pred, confidences=conf,
        per_kind=_per_kind_accuracy(pred, labels, kinds, test_mask),
    )
