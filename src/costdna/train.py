"""Training loop for the GraphSAGE classifier."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch
import torch.nn.functional as F
from sklearn.metrics import accuracy_score, classification_report

from costdna.model import GraphSAGEClassifier, supervised_contrastive_loss


@dataclass
class TrainResult:
    model: GraphSAGEClassifier
    train_acc: float
    test_acc: float
    report: str
    predictions: np.ndarray   # one prediction per node (in node order)
    confidences: np.ndarray   # max softmax prob per node
    embeddings: np.ndarray    # final hidden representation per node


def _make_split(labeled_mask: torch.Tensor, train_frac: float, seed: int,
                labels: torch.Tensor | None = None):
    """Stratified train/test split: guarantee each class shows up in both sides
    of the split when possible. Critical for small-data regimes where a single
    random shuffle can leave a class entirely out of test (or train) and
    produce misleading 0% / 100% scores.
    """
    rng = np.random.default_rng(seed)
    idx = np.where(labeled_mask.cpu().numpy())[0]

    if labels is None:
        rng.shuffle(idx)
        cut = int(len(idx) * train_frac)
        train_idx, test_idx = idx[:cut], idx[cut:]
    else:
        # Stratify by class.
        y = labels.cpu().numpy()
        train_idx, test_idx = [], []
        for cls in np.unique(y[idx]):
            cls_idx = idx[y[idx] == cls]
            rng.shuffle(cls_idx)
            cut = max(1, int(len(cls_idx) * train_frac))
            train_idx.extend(cls_idx[:cut])
            # Only put into test if there's >1 sample of this class.
            if len(cls_idx) > 1:
                test_idx.extend(cls_idx[cut:])
        train_idx, test_idx = np.array(train_idx), np.array(test_idx)

    train = torch.zeros_like(labeled_mask)
    test = torch.zeros_like(labeled_mask)
    train[train_idx] = True
    if len(test_idx) > 0:
        test[test_idx] = True
    return train, test


def train_model(
    data,
    n_classes: int,
    *,
    hidden_dim: int = 16,
    epochs: int = 200,
    lr: float = 0.01,
    weight_decay: float = 5e-4,
    train_frac: float = 0.7,
    contrastive_weight: float = 0.0,   # tuned: hurts on small/sparse data
    seed: int = 7,
    verbose: bool = True,
    n_layers: int = 4,
    dropout: float = 0.0,
    auto_small_data: bool = True,
    early_stop_patience: int = 10,
) -> TrainResult:
    torch.manual_seed(seed)
    np.random.seed(seed)

    # Auto-shrink architecture when there isn't enough labeled data to support
    # a 4-layer / hidden=16 model (~6500 parameters). The 4-layer config was
    # tuned on the synthetic env where we have 50+ labeled nodes; on real-AWS
    # accounts with 15 labels it overfits hard (train=100%, test=0% by epoch
    # 20). Below ~30 labels we switch to a 2-layer / hidden=8 / dropout=0.4
    # architecture that has ~10x fewer parameters and generalizes much better.
    n_labeled = int(data.labeled_mask.sum())
    if auto_small_data and n_labeled < 30:
        if verbose:
            print(f"  small-data mode: {n_labeled} labels → "
                  f"2 layers, hidden=8, dropout=0.4, weight_decay=1e-3")
        n_layers = 2
        hidden_dim = 8
        dropout = 0.4
        weight_decay = 1e-3

    model = GraphSAGEClassifier(
        in_dim=data.x.size(1), hidden_dim=hidden_dim, n_classes=n_classes,
        n_layers=n_layers, dropout=dropout,
    )
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)

    train_mask, test_mask = _make_split(
        data.labeled_mask, train_frac, seed, labels=data.y
    )

    best_train_acc = 0.0
    plateau_count = 0

    # Class-weighted loss: when stratified-split leaves any class with very
    # few training samples, weight rare classes higher so the model doesn't
    # learn to ignore them. Inverse frequency, normalized to mean=1.
    train_y = data.y[train_mask].cpu().numpy()
    cls_counts = np.bincount(train_y, minlength=n_classes).astype(np.float32)
    cls_counts = np.where(cls_counts == 0, 1.0, cls_counts)  # avoid div-by-0
    inv_freq = (cls_counts.mean() / cls_counts)
    cls_weights = torch.tensor(inv_freq, dtype=torch.float32, device=data.x.device)
    if verbose and n_labeled < 30:
        print(f"  class weights: {dict(zip(range(n_classes), inv_freq.round(2).tolist()))}")

    for epoch in range(1, epochs + 1):
        model.train()
        opt.zero_grad()
        logits, emb = model(data.x, data.edge_index)
        ce = F.cross_entropy(logits[train_mask], data.y[train_mask],
                             weight=cls_weights)
        cont = supervised_contrastive_loss(emb, data.y, train_mask)
        loss = ce + contrastive_weight * cont
        loss.backward()
        opt.step()

        # Early stopping: once train accuracy is saturated and loss is tiny,
        # additional epochs only deepen the overfit.
        with torch.no_grad():
            model.eval()
            pred = model(data.x, data.edge_index)[0].argmax(dim=1)
            tr_acc = (pred[train_mask] == data.y[train_mask]).float().mean().item()
        if tr_acc >= best_train_acc and loss.item() < 1e-3:
            plateau_count += 1
        else:
            plateau_count = 0
            best_train_acc = max(best_train_acc, tr_acc)
        if plateau_count >= early_stop_patience and epoch >= 20:
            if verbose:
                print(f"  epoch {epoch:3d}  early stop "
                      f"(train converged for {plateau_count} epochs)")
            break

        if verbose and (epoch % 20 == 0 or epoch == 1):
            with torch.no_grad():
                te = ((pred[test_mask] == data.y[test_mask]).float().mean().item()
                      if test_mask.any() else float("nan"))
            print(f"  epoch {epoch:3d}  loss={loss.item():.3f}  "
                  f"train={tr_acc:.3f}  test={te:.3f}")

    # Final evaluation.
    model.eval()
    with torch.no_grad():
        logits, emb = model(data.x, data.edge_index)
        probs = F.softmax(logits, dim=1)
        pred = probs.argmax(dim=1)
        confidences = probs.max(dim=1).values

    train_acc = accuracy_score(data.y[train_mask].cpu(), pred[train_mask].cpu())
    if test_mask.any():
        test_acc = accuracy_score(data.y[test_mask].cpu(), pred[test_mask].cpu())
        report = classification_report(
            data.y[test_mask].cpu().numpy(),
            pred[test_mask].cpu().numpy(),
            zero_division=0,
        )
    else:
        test_acc = float("nan")
        report = "(no test set)"

    return TrainResult(
        model=model,
        train_acc=float(train_acc),
        test_acc=float(test_acc),
        report=report,
        predictions=pred.cpu().numpy(),
        confidences=confidences.cpu().numpy(),
        embeddings=emb.cpu().numpy(),
    )
