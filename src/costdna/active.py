"""Active learning — turn 30 confirmed labels into thousands of attributions.

In real environments nobody has clean labels. They have a few tagged resources,
some Slack tribal knowledge, and 60% mystery. Active learning closes that gap:
the model surfaces its lowest-confidence guesses, an operator confirms them,
the model retrains. Each label is targeted at the resource that improves the
model most.

Three acquisition strategies:

  random            — baseline; pick uniformly at random from unlabeled
  least_confidence  — pick whichever resource the model is least sure about
  margin            — pick whichever has the smallest gap between top-1 and
                      top-2 predictions (decision-boundary uncertainty)

This module simulates the loop using ground truth as the "operator" — in
production you'd swap in a CLI prompt or a Slack approve-button.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch
import torch.nn.functional as F

from costdna.model import GraphSAGEClassifier


@dataclass
class ALStep:
    n_labels: int
    test_acc: float
    overall_acc: float       # accuracy across ALL nodes (including labeled)
    newly_labeled: list[str]


@dataclass
class ALResult:
    strategy: str
    history: list[ALStep]


def _train_quick(data, n_classes: int, train_mask: torch.Tensor,
                 epochs: int = 100, lr: float = 0.01, seed: int = 7,
                 hidden_dim: int = 32):
    torch.manual_seed(seed)
    model = GraphSAGEClassifier(in_dim=data.x.size(1),
                                hidden_dim=hidden_dim, n_classes=n_classes)
    opt = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=5e-4)
    for _ in range(epochs):
        model.train()
        opt.zero_grad()
        logits, _ = model(data.x, data.edge_index)
        if not train_mask.any():
            break
        F.cross_entropy(logits[train_mask], data.y[train_mask]).backward()
        opt.step()
    model.eval()
    with torch.no_grad():
        logits, _ = model(data.x, data.edge_index)
        probs = F.softmax(logits, dim=1)
    return probs.cpu().numpy()


def _acquire(probs: np.ndarray, candidates: np.ndarray, strategy: str,
             batch_size: int, rng: np.random.Generator) -> np.ndarray:
    if strategy == "random":
        return rng.choice(candidates, size=min(batch_size, len(candidates)), replace=False)

    if strategy == "least_confidence":
        scores = probs[candidates].max(axis=1)              # higher = more confident
        order = np.argsort(scores)                          # ascending → least confident first
        return candidates[order[:batch_size]]

    if strategy == "margin":
        sorted_p = np.sort(probs[candidates], axis=1)
        margin = sorted_p[:, -1] - sorted_p[:, -2]          # top-1 minus top-2
        order = np.argsort(margin)                          # smallest margin first
        return candidates[order[:batch_size]]

    raise ValueError(f"unknown strategy: {strategy!r}")


def active_learning_loop(
    data,
    n_classes: int,
    *,
    initial_labels: int = 4,
    budget: int = 30,
    batch_size: int = 2,
    strategy: str = "least_confidence",
    seed: int = 0,
) -> ALResult:
    """Simulate the loop. data must already have y and labeled_mask set.

    Returns the accuracy curve as we add labels under the chosen strategy.
    """
    rng = np.random.default_rng(seed)
    available = np.where(data.labeled_mask.cpu().numpy())[0]
    rng.shuffle(available)
    n_total = data.y.size(0)

    # Carve out a held-out test set first — never let it leak into training.
    test_size = max(int(0.3 * len(available)), 1)
    test_idx = available[:test_size]
    pool = available[test_size:]

    # Seed the training set with `initial_labels` random labels.
    train_idx = list(pool[:initial_labels])
    pool = pool[initial_labels:].tolist()

    history: list[ALStep] = []
    y_true = data.y.cpu().numpy()
    node_ids = getattr(data, "node_ids", list(range(n_total)))

    while True:
        train_mask = torch.zeros(n_total, dtype=torch.bool)
        train_mask[train_idx] = True

        probs = _train_quick(data, n_classes, train_mask, seed=seed + len(train_idx))
        pred = probs.argmax(axis=1)

        test_acc = float((pred[test_idx] == y_true[test_idx]).mean())
        overall = float((pred[available] == y_true[available]).mean())
        history.append(ALStep(
            n_labels=len(train_idx), test_acc=test_acc, overall_acc=overall,
            newly_labeled=[node_ids[i] for i in train_idx[-batch_size:]] if history else [],
        ))

        if len(train_idx) >= budget or not pool:
            break

        candidates = np.array([i for i in pool if i not in test_idx], dtype=int)
        picks = _acquire(probs, candidates, strategy, batch_size, rng)
        train_idx.extend(int(p) for p in picks)
        pool = [i for i in pool if i not in set(int(p) for p in picks)]

    return ALResult(strategy=strategy, history=history)
