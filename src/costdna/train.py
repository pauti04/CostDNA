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


def _make_split(labeled_mask: torch.Tensor, train_frac: float, seed: int):
    rng = np.random.default_rng(seed)
    idx = np.where(labeled_mask.cpu().numpy())[0]
    rng.shuffle(idx)
    cut = int(len(idx) * train_frac)
    train = torch.zeros_like(labeled_mask)
    test = torch.zeros_like(labeled_mask)
    train[idx[:cut]] = True
    test[idx[cut:]] = True
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
) -> TrainResult:
    torch.manual_seed(seed)
    np.random.seed(seed)

    model = GraphSAGEClassifier(
        in_dim=data.x.size(1), hidden_dim=hidden_dim, n_classes=n_classes,
        n_layers=n_layers,
    )
    opt = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=weight_decay)

    train_mask, test_mask = _make_split(data.labeled_mask, train_frac, seed)

    for epoch in range(1, epochs + 1):
        model.train()
        opt.zero_grad()
        logits, emb = model(data.x, data.edge_index)
        ce = F.cross_entropy(logits[train_mask], data.y[train_mask])
        cont = supervised_contrastive_loss(emb, data.y, train_mask)
        loss = ce + contrastive_weight * cont
        loss.backward()
        opt.step()

        if verbose and (epoch % 20 == 0 or epoch == 1):
            model.eval()
            with torch.no_grad():
                logits, _ = model(data.x, data.edge_index)
                pred = logits.argmax(dim=1)
                tr = (pred[train_mask] == data.y[train_mask]).float().mean().item()
                te = ((pred[test_mask] == data.y[test_mask]).float().mean().item()
                      if test_mask.any() else float("nan"))
            print(f"  epoch {epoch:3d}  loss={loss.item():.3f}  "
                  f"train={tr:.3f}  test={te:.3f}")

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
