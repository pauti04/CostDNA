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


def _node2vec_walks(
    graph: nx.Graph, node_ids: list[str],
    *, walk_length: int, walks_per_node: int,
    p: float, q: float, rng: np.random.Generator,
) -> list[list[str]]:
    """Generate biased random walks per Grover & Leskovec (2016).

    p controls likelihood of revisiting the previous node (smaller = more
    backtracking); q controls outward exploration (smaller = more outward
    DFS-like walks). p=q=1 reduces to uniform random walks (DeepWalk).

    Pure-Python implementation — avoids the torch-cluster binary dependency
    that PyG's built-in Node2Vec module requires. The walks themselves are
    cheap (linear in walk_length * walks_per_node * n); the expensive part
    is the downstream skip-gram embedding which gensim handles.
    """
    neighbors = {n: list(graph.neighbors(n)) for n in node_ids}
    walks: list[list[str]] = []
    for _ in range(walks_per_node):
        order = list(node_ids)
        rng.shuffle(order)
        for start in order:
            if not neighbors[start]:
                walks.append([start])
                continue
            walk = [start]
            prev = None
            for _ in range(walk_length - 1):
                cur = walk[-1]
                cands = neighbors[cur]
                if not cands:
                    break
                if prev is None or p == 1.0 and q == 1.0:
                    # First step or unbiased — uniform sample.
                    nxt = cands[int(rng.integers(0, len(cands)))]
                else:
                    # Biased step. Compute unnormalized probabilities for each
                    # candidate based on its distance from prev:
                    #   d(prev, x) = 0 → weight 1/p (return)
                    #   d(prev, x) = 1 → weight 1   (same-level)
                    #   d(prev, x) = 2 → weight 1/q (further out)
                    prev_neighbors = set(neighbors[prev])
                    weights = np.empty(len(cands), dtype=np.float64)
                    for i, x in enumerate(cands):
                        if x == prev:
                            weights[i] = 1.0 / p
                        elif x in prev_neighbors:
                            weights[i] = 1.0
                        else:
                            weights[i] = 1.0 / q
                    weights /= weights.sum()
                    nxt = cands[int(rng.choice(len(cands), p=weights))]
                walk.append(nxt)
                prev = cur
            walks.append(walk)
    return walks


def run_node2vec(
    graph: nx.Graph, node_ids: list[str], features: np.ndarray,
    labels: np.ndarray, train_mask: np.ndarray, test_mask: np.ndarray,
    kinds: list[str],
    *,
    embedding_dim: int = 64,
    walk_length: int = 20,
    context_size: int = 10,
    walks_per_node: int = 10,
    p: float = 1.0,
    q: float = 1.0,
    n_epochs: int = 5,
    seed: int = 42,
) -> BaselineResult:
    """Node2Vec embedding + classifier — the strongest non-message-passing graph baseline.

    Node2Vec (Grover & Leskovec, 2016) learns node embeddings from biased
    random walks over the graph, without using node features directly. We
    then train a LogisticRegression classifier on the concatenation of
    [node2vec_embedding, behavioral_features].

    The point of this baseline: if GraphSAGE only marginally beats node2vec+LR,
    then the message-passing machinery isn't earning its complexity — node2vec's
    random walks pick up the same structural signal more cheaply. If GraphSAGE
    wins meaningfully, the inductive bias of message-passing (combining neighbor
    aggregation with input features in a learned, end-to-end way) is what
    matters.

    Notes
    -----
    - We concatenate node2vec embeddings with the same behavioral features the
      GNN sees. The fair head-to-head is "node2vec replaces the message-passing
      layer, everything else equal."
    - Implementation uses pure-Python biased random walks + gensim Word2Vec
      for skip-gram training. We deliberately avoid PyG's
      ``torch_geometric.nn.Node2Vec``, which requires the ``torch-cluster``
      binary wheel — that wheel must match the installed torch version and
      often fails to install cleanly on Macs. The pure-Python walks are
      cheap; gensim handles the heavy lifting of skip-gram training.
    - Training is unsupervised; the labels are only used for the downstream
      LogReg fit on the train_mask split.
    - Defaults (p=q=1) reduce to DeepWalk (uniform random walks). Setting
      p<1 biases toward BFS-like local walks; q<1 biases toward DFS-like
      outward walks. See Grover & Leskovec §3.2.
    """
    try:
        from gensim.models import Word2Vec
    except ImportError as exc:
        raise ImportError(
            "node2vec baseline requires gensim. Install with: pip install gensim"
        ) from exc

    n = len(node_ids)

    # Map graph nodes to a stable indexed position so the downstream feature
    # concatenation lines up with the input arrays.
    pos_of = {nid: i for i, nid in enumerate(node_ids)}

    # Edge-case: graph with no edges. Fall back to features-only LogReg so the
    # baseline still produces a defensible row in the comparison table rather
    # than crashing. Exercised by tiny test fixtures, not production runs.
    if graph.number_of_edges() == 0:
        return run_logistic_regression(features, labels, train_mask, test_mask, kinds)

    rng = np.random.default_rng(seed)
    eff_walk_length = max(2, walk_length)
    eff_context = max(1, min(context_size, eff_walk_length - 1))

    walks = _node2vec_walks(
        graph, node_ids,
        walk_length=eff_walk_length, walks_per_node=walks_per_node,
        p=p, q=q, rng=rng,
    )
    # gensim expects walks as lists of string tokens.
    sentences = [[str(node) for node in walk] for walk in walks if len(walk) >= 2]

    w2v = Word2Vec(
        sentences=sentences,
        vector_size=embedding_dim,
        window=eff_context,
        min_count=0,        # ensure every node gets an embedding even if rare
        sg=1,               # skip-gram (faithful to the node2vec paper)
        workers=1,          # determinism
        seed=seed,
        epochs=n_epochs,
        negative=5,
    )

    # Build the dense embedding matrix in node_ids order. Nodes that never
    # appeared in any walk (isolated) get a zero vector.
    emb = np.zeros((n, embedding_dim), dtype=np.float32)
    for nid in node_ids:
        key = str(nid)
        if key in w2v.wv:
            emb[pos_of[nid]] = w2v.wv[key]

    # Concatenate node2vec embedding with the behavioral features. Same inputs
    # as the GNN sees; different aggregation strategy.
    X = np.concatenate([emb, features], axis=1)

    clf = LogisticRegression(max_iter=2000, class_weight="balanced", C=1.0)
    clf.fit(X[train_mask], labels[train_mask])
    pred = clf.predict(X)
    conf = clf.predict_proba(X).max(axis=1)
    return BaselineResult(
        name="node2vec+LR",
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
