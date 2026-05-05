"""Graph construction.

Nodes  — one per resource, attribute is the feature vector.
Edges  — two sources, both bidirectional and weight-summed:

  1. Network edges from VPC flow logs (weight ∝ log10(bytes + 1))
  2. IAM-role edges: if the same role touches resource A and resource B,
     add an edge between them.

Why both? Network edges capture data-plane affinity; IAM edges capture
control-plane affinity. Some teams have one signal but not the other (e.g. a
serverless team has weak VPC traffic but strong IAM signal), and the GNN's job
is easier with both available.
"""

from __future__ import annotations

import math
from collections import defaultdict

import networkx as nx
import numpy as np
import pandas as pd


def build_graph(
    features: pd.DataFrame,
    metadata: pd.DataFrame,
    flows: pd.DataFrame,
    signals: pd.DataFrame,
    edge_kinds: tuple[str, ...] = ("network", "iam", "vpc"),
) -> nx.Graph:
    """Build the graph with the requested edge kinds enabled.

    Each edge tracks all the kinds that contributed to it (a single edge can
    represent both network traffic AND a shared IAM role). Ablation works by
    rebuilding with one kind disabled — e.g., `edge_kinds=('network', 'vpc')`
    means "what would the graph look like if we never knew about IAM roles?"
    """
    g = nx.Graph()

    feat_arr = features.values.astype(np.float32)
    for rid, vec in zip(features.index, feat_arr):
        g.add_node(rid, x=vec)

    def _add_or_update(a: str, b: str, weight: float, kind: str) -> None:
        if g.has_edge(a, b):
            g[a][b]["weight"] += weight
            g[a][b]["kinds"].add(kind)
        else:
            g.add_edge(a, b, weight=weight, kinds={kind})

    if "network" in edge_kinds and not flows.empty \
            and {"src", "dst", "bytes"}.issubset(flows.columns):
        for _, row in flows.iterrows():
            s, d = row["src"], row["dst"]
            if s == d or s not in g or d not in g:
                continue
            w = math.log10(float(row["bytes"]) + 1)
            _add_or_update(s, d, w, "network")

    if "iam" in edge_kinds and not signals.empty and "iam_role" in signals.columns:
        role_to_resources: dict[str, set] = defaultdict(set)
        for rid, role in signals[["resource_id", "iam_role"]].dropna().itertuples(index=False):
            if rid in g.nodes and role:
                role_to_resources[role].add(rid)
        for role, rids in role_to_resources.items():
            rids = list(rids)
            for i in range(len(rids)):
                for j in range(i + 1, len(rids)):
                    _add_or_update(rids[i], rids[j], 1.0, "iam")

    if "vpc" in edge_kinds and "vpc_cidr" in metadata.columns:
        vpc_groups: dict[str, list] = defaultdict(list)
        for rid, vpc in metadata[["resource_id", "vpc_cidr"]].itertuples(index=False):
            if vpc and rid in g.nodes:
                vpc_groups[vpc].append(rid)
        for rids in vpc_groups.values():
            for i in range(len(rids)):
                for j in range(i + 1, len(rids)):
                    _add_or_update(rids[i], rids[j], 0.5, "vpc")

    return g


def to_pyg(graph: nx.Graph, labels: dict[str, int] | None = None):
    """Convert a NetworkX graph + optional label dict to a PyTorch Geometric Data object.

    Done by hand (rather than via from_networkx) so we control the node ordering
    and label alignment exactly.
    """
    import torch
    from torch_geometric.data import Data

    nodes = list(graph.nodes)
    idx = {n: i for i, n in enumerate(nodes)}
    x = np.stack([graph.nodes[n]["x"] for n in nodes]).astype(np.float32)

    edge_src, edge_dst, edge_w = [], [], []
    for u, v, data in graph.edges(data=True):
        i, j = idx[u], idx[v]
        w = float(data.get("weight", 1.0))
        edge_src.extend([i, j])
        edge_dst.extend([j, i])
        edge_w.extend([w, w])

    if not edge_src:
        edge_src, edge_dst, edge_w = [0], [0], [0.0]

    data = Data(
        x=torch.tensor(x),
        edge_index=torch.tensor([edge_src, edge_dst], dtype=torch.long),
        edge_weight=torch.tensor(edge_w, dtype=torch.float32),
    )
    data.node_ids = nodes

    if labels is not None:
        y = np.full(len(nodes), -1, dtype=np.int64)
        labeled_mask = np.zeros(len(nodes), dtype=bool)
        for n, label in labels.items():
            if n in idx:
                y[idx[n]] = label
                labeled_mask[idx[n]] = True
        data.y = torch.tensor(y, dtype=torch.long)
        data.labeled_mask = torch.tensor(labeled_mask, dtype=torch.bool)
    return data
