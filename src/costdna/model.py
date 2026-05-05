"""GraphSAGE classifier with residual connections and a tunable depth.

Why GraphSAGE: the inductive setting (we want to classify newly-seen resources
on each scan) needs a model that aggregates neighbor features rather than
learning a fixed embedding per node like classical GCN. SAGE does exactly that.

Architecture decisions:
  - 4 layers by default — empirically the sweet spot on real Azure data.
    2 layers underfit (graph signal doesn't propagate far enough).
    6+ layers overfit (variance jumps).
  - Residual connections let later layers refine without losing early signal.
  - An input projection brings raw features into hidden_dim so residuals work
    when in_dim != hidden_dim.
  - hidden_dim=16 was tuned for the typical small-feature-vector regime
    (8-16 features). Override for richer feature spaces.
  - Dropout off by default — empirically hurts on the small datasets we run.
"""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import SAGEConv


class GraphSAGEClassifier(nn.Module):
    def __init__(self, in_dim: int, hidden_dim: int = 16, n_classes: int = 3,
                 n_layers: int = 4, dropout: float = 0.0,
                 residual: bool = True):
        super().__init__()
        self.residual = residual
        self.dropout = dropout
        self.input_proj = nn.Linear(in_dim, hidden_dim) if residual else None
        self.convs = nn.ModuleList()
        first_in = hidden_dim if residual else in_dim
        self.convs.append(SAGEConv(first_in, hidden_dim))
        for _ in range(n_layers - 1):
            self.convs.append(SAGEConv(hidden_dim, hidden_dim))
        self.classifier = nn.Linear(hidden_dim, n_classes)

    def encode(self, x: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
        h = self.input_proj(x) if self.residual else x
        prev = None
        for i, conv in enumerate(self.convs):
            new = conv(h, edge_index)
            if i < len(self.convs) - 1:
                new = F.relu(new)
                if self.dropout > 0:
                    new = F.dropout(new, p=self.dropout, training=self.training)
            if self.residual and prev is not None and h.shape == new.shape:
                h = new + prev
            else:
                h = new
            prev = h
        return h

    def forward(self, x: torch.Tensor, edge_index: torch.Tensor
                ) -> tuple[torch.Tensor, torch.Tensor]:
        h = self.encode(x, edge_index)
        logits = self.classifier(h)
        return logits, h


def supervised_contrastive_loss(embeddings: torch.Tensor, labels: torch.Tensor,
                                mask: torch.Tensor, temperature: float = 0.5) -> torch.Tensor:
    """Pulls same-team embeddings together, pushes different-team embeddings apart.

    Operates only on labeled nodes (mask). Returns 0 if there's <2 labeled nodes
    or only one represented class.
    """
    emb = embeddings[mask]
    lab = labels[mask]
    if emb.size(0) < 2 or lab.unique().numel() < 2:
        return torch.tensor(0.0, device=embeddings.device)

    emb = F.normalize(emb, dim=1)
    sim = emb @ emb.T / temperature

    # Mask self-similarities. Use a large negative number rather than -inf so
    # that downstream `0 * -inf = nan` doesn't poison the loss.
    eye = torch.eye(sim.size(0), dtype=torch.bool, device=sim.device)
    sim = sim.masked_fill(eye, -1e9)

    same = (lab.unsqueeze(0) == lab.unsqueeze(1)).float()
    same = same.masked_fill(eye, 0)

    # Only sum log-prob over the non-self entries (mask the diagonal explicitly).
    log_prob = sim - torch.logsumexp(sim, dim=1, keepdim=True)
    log_prob = log_prob.masked_fill(eye, 0.0)

    pos_count = same.sum(dim=1).clamp(min=1)
    loss = -(same * log_prob).sum(dim=1) / pos_count
    return loss.mean()
