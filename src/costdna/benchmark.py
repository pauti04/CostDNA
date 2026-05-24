"""Run every model side-by-side on the same data and graph.

Produces the comparison table that's the actual research artifact: which
component (features? graph structure? GNN combining both?) is doing the work,
on which kinds of resources, and **with what variance across random seeds**.

Single-seed numbers are vibes — a 100%-vs-89% gap can flip on a different
data shuffle. The multi-seed runner reports mean ± std across N seeds, which
is what makes this defensible.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import networkx as nx
import numpy as np
import torch
from sklearn.metrics import confusion_matrix as sk_confusion

from costdna import TEAMS
from costdna.baselines import (BaselineResult, majority_baseline,
                               run_knn, run_label_propagation,
                               run_logistic_regression, run_node2vec)
from costdna.train import TrainResult


@dataclass
class BenchmarkRow:
    name: str
    train_acc: float
    test_acc: float
    per_kind: dict[str, float]
    predictions: np.ndarray
    confusion: np.ndarray
    confidences: np.ndarray = field(default_factory=lambda: np.array([]))


def _to_row(name: str, pred: np.ndarray, conf: np.ndarray, train_acc: float,
            test_acc: float, per_kind: dict[str, float], y: np.ndarray,
            test_mask: np.ndarray, n_classes: int) -> BenchmarkRow:
    cm = sk_confusion(y[test_mask], pred[test_mask],
                      labels=list(range(n_classes)))
    return BenchmarkRow(name=name, train_acc=train_acc, test_acc=test_acc,
                        per_kind=per_kind, predictions=pred,
                        confusion=cm, confidences=conf)


def run_benchmark(
    data,
    graph: nx.Graph,
    features_arr: np.ndarray,
    kinds: list[str],
    n_classes: int = len(TEAMS),
    *,
    train_frac: float = 0.7,
    seed: int = 7,
    epochs: int = 200,
) -> tuple[list[BenchmarkRow], TrainResult]:
    """Returns (rows, gnn_result). Each row is one model's full result."""
    rng = np.random.default_rng(seed)
    labeled = data.labeled_mask.cpu().numpy()
    labeled_idx = np.where(labeled)[0]

    # Stratify by `kind`: each kind gets the same train/test split fraction.
    # This guarantees the test set actually contains hard cases — otherwise
    # the rare ones (sparse, shared_service) get hidden in the train set.
    train_mask = np.zeros_like(labeled)
    test_mask = np.zeros_like(labeled)
    by_kind: dict[str, list[int]] = {}
    for i in labeled_idx:
        by_kind.setdefault(kinds[i], []).append(int(i))
    for kind, members in by_kind.items():
        rng.shuffle(members)
        cut = max(1, int(len(members) * train_frac))
        train_mask[members[:cut]] = True
        if len(members) > cut:
            test_mask[members[cut:]] = True

    y = data.y.cpu().numpy()

    rows: list[BenchmarkRow] = []

    node_ids = list(graph.nodes)
    for fn, name_args in [
        (lambda: majority_baseline(y, train_mask, test_mask, kinds, n_classes), ()),
        (lambda: run_logistic_regression(features_arr, y, train_mask, test_mask, kinds), ()),
        (lambda: run_knn(features_arr, y, train_mask, test_mask, kinds), ()),
        (lambda: run_label_propagation(graph, node_ids, y,
                                       train_mask, test_mask, kinds, n_classes), ()),
        # Node2Vec is the strongest non-message-passing graph baseline. If
        # GraphSAGE only marginally beats it, the message-passing machinery
        # isn't earning its complexity.
        (lambda: run_node2vec(graph, node_ids, features_arr, y,
                              train_mask, test_mask, kinds, seed=seed), ()),
    ]:
        b: BaselineResult = fn()
        rows.append(_to_row(b.name, b.predictions, b.confidences, b.train_acc,
                            b.test_acc, b.per_kind, y, test_mask, n_classes))

    # Re-run the GNN with the same fixed split so the comparison is apples-to-apples.
    train_mask_t = torch.tensor(train_mask)
    # Patch the data's split via a custom training call.
    gnn_result = _train_with_fixed_split(data, n_classes, train_mask_t,
                                         torch.tensor(test_mask),
                                         epochs=epochs, seed=seed)
    gnn_per_kind = {}
    for kind in set(kinds):
        idx = np.array([i for i, k in enumerate(kinds)
                        if k == kind and test_mask[i] and y[i] >= 0])
        if len(idx):
            gnn_per_kind[kind] = float((gnn_result.predictions[idx] == y[idx]).mean())
    rows.append(_to_row("GraphSAGE", gnn_result.predictions, gnn_result.confidences,
                        gnn_result.train_acc, gnn_result.test_acc, gnn_per_kind,
                        y, test_mask, n_classes))
    return rows, gnn_result


def _train_with_fixed_split(data, n_classes, train_mask, test_mask, epochs, seed):
    """Train GNN with externally-supplied split (so it matches the baselines).

    Auto-shrinks for small labeled sets (<30 labels): 2 layers / hidden=8 /
    dropout=0.4 instead of the 4-layer / hidden=16 default. Early-stops on
    train convergence to avoid the 'train=100% / test=0% by epoch 20'
    overfit pattern observed on real-AWS scans.
    """
    torch.manual_seed(seed)
    np.random.seed(seed)
    import torch.nn.functional as F
    from sklearn.metrics import accuracy_score, classification_report

    from costdna.model import GraphSAGEClassifier

    torch.manual_seed(seed)
    np.random.seed(seed)

    n_labeled = int(train_mask.sum() + test_mask.sum())
    if n_labeled < 30:
        n_layers, hidden_dim, dropout, weight_decay = 2, 8, 0.4, 1e-3
    else:
        n_layers, hidden_dim, dropout, weight_decay = 4, 16, 0.0, 5e-4

    # SAGE is the consistent winner across both regimes:
    # - On <30 labels, GAT's attention parameters collapse to random
    # - On 50+ labels GAT is marginal (~+0.8%) but loses ~30 points on
    #   shared-services kind. SAGE's uniform aggregation is more robust.
    # GAT remains available via GraphSAGEClassifier(conv_type="gat") for
    # users who want to experiment in larger / cleaner graph regimes.
    model = GraphSAGEClassifier(
        in_dim=data.x.size(1), hidden_dim=hidden_dim, n_classes=n_classes,
        n_layers=n_layers, dropout=dropout, conv_type="sage",
    )
    opt = torch.optim.AdamW(model.parameters(), lr=0.01, weight_decay=weight_decay)

    # Class-weighted loss for stratified-split fairness on small data.
    train_y = data.y[train_mask].cpu().numpy()
    cls_counts = np.bincount(train_y, minlength=n_classes).astype(np.float32)
    cls_counts = np.where(cls_counts == 0, 1.0, cls_counts)
    cls_weights = torch.tensor(
        cls_counts.mean() / cls_counts, dtype=torch.float32
    )

    plateau = 0
    for ep in range(epochs):
        model.train()
        opt.zero_grad()
        logits, _ = model(data.x, data.edge_index)
        loss = F.cross_entropy(logits[train_mask], data.y[train_mask],
                               weight=cls_weights)
        loss.backward()
        opt.step()
        if n_labeled < 30 and loss.item() < 1e-3:
            plateau += 1
            if plateau >= 10 and ep >= 20:
                break
        else:
            plateau = 0

    model.eval()
    with torch.no_grad():
        logits, emb = model(data.x, data.edge_index)
        probs = F.softmax(logits, dim=1)
        pred = probs.argmax(dim=1)
        conf = probs.max(dim=1).values

    train_acc = accuracy_score(data.y[train_mask].cpu(), pred[train_mask].cpu())
    test_acc = (accuracy_score(data.y[test_mask].cpu(), pred[test_mask].cpu())
                if test_mask.any() else float("nan"))
    report = (classification_report(data.y[test_mask].cpu().numpy(),
                                    pred[test_mask].cpu().numpy(), zero_division=0)
              if test_mask.any() else "")
    return TrainResult(
        model=model, train_acc=float(train_acc), test_acc=float(test_acc),
        report=report, predictions=pred.cpu().numpy(),
        confidences=conf.cpu().numpy(), embeddings=emb.cpu().numpy(),
    )


@dataclass
class AggregatedRow:
    """Mean ± std for one model across N seeds."""
    name: str
    test_acc_mean: float
    test_acc_std: float
    per_kind_mean: dict[str, float]
    per_kind_std: dict[str, float]
    n_seeds: int
    seeds: list[int]


def aggregate_seeds(per_seed_rows: list[list[BenchmarkRow]],
                    seeds: list[int]) -> list[AggregatedRow]:
    """per_seed_rows[seed_i][model_j] -> BenchmarkRow."""
    n_seeds = len(per_seed_rows)
    n_models = len(per_seed_rows[0])
    out: list[AggregatedRow] = []
    for j in range(n_models):
        rows_for_model = [per_seed_rows[i][j] for i in range(n_seeds)]
        accs = np.array([r.test_acc for r in rows_for_model])
        kinds_seen = sorted({k for r in rows_for_model for k in r.per_kind})
        per_kind_mean = {}
        per_kind_std = {}
        for kind in kinds_seen:
            kvals = np.array([r.per_kind.get(kind, np.nan) for r in rows_for_model])
            kvals = kvals[~np.isnan(kvals)]
            if len(kvals):
                per_kind_mean[kind] = float(kvals.mean())
                per_kind_std[kind] = float(kvals.std())
        out.append(AggregatedRow(
            name=rows_for_model[0].name,
            test_acc_mean=float(accs.mean()),
            test_acc_std=float(accs.std()),
            per_kind_mean=per_kind_mean,
            per_kind_std=per_kind_std,
            n_seeds=n_seeds,
            seeds=seeds,
        ))
    return out


def run_benchmark_multiseed(
    build_data_fn,
    seeds: list[int],
    *,
    train_frac: float = 0.7,
    epochs: int = 200,
) -> list[AggregatedRow]:
    """Run the full benchmark across multiple seeds.

    `build_data_fn(seed)` returns (data, graph, features_arr, kinds) — caller
    is responsible for re-generating the synthetic data per seed if desired.
    """
    per_seed: list[list[BenchmarkRow]] = []
    for seed in seeds:
        data, graph, features_arr, kinds = build_data_fn(seed)
        rows, _ = run_benchmark(
            data, graph, features_arr, kinds,
            seed=seed, epochs=epochs, train_frac=train_frac,
        )
        per_seed.append(rows)
    return aggregate_seeds(per_seed, seeds)


def run_benchmark_kfold(
    data, graph, features_arr, kinds: list[str],
    *,
    k: int = 5,
    seed: int = 42,
    epochs: int = 200,
    n_classes: int = len(TEAMS),
) -> list[AggregatedRow]:
    """Stratified k-fold cross-validation. Each fold trains on (k-1)/k of the
    labeled data and tests on the held-out 1/k. We report the mean ± std of
    test accuracy across folds — a stricter test than a single 70/30 split.
    """
    rng = np.random.default_rng(seed)
    labeled = data.labeled_mask.cpu().numpy()
    labeled_idx = np.where(labeled)[0]

    # Stratified fold assignment.
    by_kind: dict[str, list[int]] = {}
    for i in labeled_idx:
        by_kind.setdefault(kinds[i], []).append(int(i))
    fold_of = np.full(len(labeled), -1, dtype=int)
    for kind, members in by_kind.items():
        rng.shuffle(members)
        for pos, idx in enumerate(members):
            fold_of[idx] = pos % k

    per_fold: list[list[BenchmarkRow]] = []
    for fold in range(k):
        train_mask = (fold_of != fold) & (fold_of >= 0)
        test_mask = fold_of == fold
        if not test_mask.any():
            continue
        # Hand-thread the fold's masks into run_benchmark by patching
        # data.labeled_mask. We restore it after.
        original_labeled = data.labeled_mask.clone()
        try:
            # Make benchmark use our exact split: set labeled_mask to (train | test)
            # and rely on its stratified split function to give train_frac=split.
            # Simpler: call _train_with_fixed_split directly for the GNN, and
            # call baselines explicitly with our masks.
            import torch
            from costdna.baselines import (majority_baseline, run_knn,
                                            run_label_propagation,
                                            run_logistic_regression,
                                            run_node2vec)
            y = data.y.cpu().numpy()
            node_ids = list(graph.nodes)
            rows: list[BenchmarkRow] = []
            for b in [
                majority_baseline(y, train_mask, test_mask, kinds, n_classes),
                run_logistic_regression(features_arr, y, train_mask, test_mask, kinds),
                run_knn(features_arr, y, train_mask, test_mask, kinds),
                run_label_propagation(graph, node_ids, y, train_mask,
                                      test_mask, kinds, n_classes),
                run_node2vec(graph, node_ids, features_arr, y, train_mask,
                             test_mask, kinds, seed=seed + fold),
            ]:
                rows.append(_to_row(b.name, b.predictions, b.confidences,
                                    b.train_acc, b.test_acc, b.per_kind,
                                    y, test_mask, n_classes))
            gnn_result = _train_with_fixed_split(
                data, n_classes,
                torch.tensor(train_mask), torch.tensor(test_mask),
                epochs=epochs, seed=seed + fold,
            )
            gnn_per_kind = {}
            for kind in set(kinds):
                idx = np.array([i for i, kk in enumerate(kinds)
                                if kk == kind and test_mask[i] and y[i] >= 0])
                if len(idx):
                    gnn_per_kind[kind] = float((gnn_result.predictions[idx] == y[idx]).mean())
            rows.append(_to_row("GraphSAGE", gnn_result.predictions,
                                gnn_result.confidences, gnn_result.train_acc,
                                gnn_result.test_acc, gnn_per_kind, y,
                                test_mask, n_classes))
            per_fold.append(rows)
        finally:
            data.labeled_mask = original_labeled

    return aggregate_seeds(per_fold, [seed + i for i in range(len(per_fold))])


def attributed_dollars(signals, metadata, predictions: np.ndarray,
                       node_ids: list[str], teams: tuple[str, ...]) -> dict:
    """Aggregate $ per predicted team. Headline number for the demo: how much
    spend would have been unowned without CostDNA."""
    cost = signals[signals["signal_type"] == "cost"]
    cost_by_resource = cost.groupby("resource_id")["value"].sum().to_dict()

    pred_team = {rid: teams[int(p)] for rid, p in zip(node_ids, predictions)}
    by_team: dict[str, float] = {t: 0.0 for t in teams}
    n_resources: dict[str, int] = {t: 0 for t in teams}

    for rid, total in cost_by_resource.items():
        team = pred_team.get(rid)
        if team is None:
            continue
        by_team[team] += float(total)
        n_resources[team] += 1

    total = sum(by_team.values())
    return {
        "total": total,
        "by_team": by_team,
        "resources_per_team": n_resources,
    }
