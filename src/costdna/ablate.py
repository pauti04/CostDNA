"""Feature & edge ablation.

For each feature group and each edge type, train the GNN with that component
removed and report the accuracy delta. The component with the biggest drop is
the one carrying the load. The component with no drop is dead weight.

Output is the table you publish in the README to justify every architectural
choice.
"""

from __future__ import annotations

from dataclasses import dataclass

import networkx as nx
import numpy as np
import pandas as pd

from costdna import TEAMS
from costdna.graph import build_graph, to_pyg
from costdna.train import train_model


# Group features by what they capture, so we ablate by group rather than by
# individual column (a single column rarely carries a story by itself).
FEATURE_GROUPS = {
    "activity":   ["event_count", "unique_users", "unique_roles"],
    "schedule":   ["peak_hour", "weekend_ratio"],
    "topology":   ["cross_account"],
    "cost_shape": ["cost_slope", "cost_variance", "cost_autocorr"],
}

EDGE_KINDS = ("network", "iam", "vpc")


@dataclass
class AblationRow:
    component: str
    test_acc: float
    delta: float


def _drop_features(features: pd.DataFrame, drop_cols: list[str]) -> pd.DataFrame:
    keep = [c for c in features.columns if c not in drop_cols]
    if not keep:
        # If we dropped everything, leave a constant column so PyG doesn't choke.
        return pd.DataFrame(np.zeros((len(features), 1)), index=features.index,
                            columns=["_zero"])
    return features[keep]


def _drop_edge_kind(graph: nx.Graph, kind_to_drop: str) -> nx.Graph:
    """Return a copy of `graph` with all edges of `kind_to_drop` removed.

    Edges that mix kinds (e.g. network + iam) keep the other kinds and have
    their weight reduced proportionally — modeling "what if we hadn't known
    about IAM roles" rather than "delete every edge that touched IAM."
    """
    g = nx.Graph()
    for n, attrs in graph.nodes(data=True):
        g.add_node(n, **attrs)
    for u, v, data in graph.edges(data=True):
        kinds = data.get("kinds", set())
        if kinds == {kind_to_drop}:
            continue
        remaining = kinds - {kind_to_drop}
        if not remaining:
            continue
        # Approximate the weight contribution of remaining kinds by scaling.
        new_weight = data["weight"] * (len(remaining) / max(len(kinds), 1))
        g.add_edge(u, v, weight=new_weight, kinds=remaining)
    return g


def run_feature_ablation(
    features: pd.DataFrame,
    graph: nx.Graph,
    labels: dict[str, int],
    *,
    n_classes: int = len(TEAMS),
    epochs: int = 200,
    seeds: list[int] = (1, 2, 3, 4, 5),
) -> tuple[float, list[AblationRow]]:
    """Returns (full_acc, ablation_rows). Every row is one feature group dropped."""
    full_accs = []
    for s in seeds:
        data = to_pyg(graph, labels)
        full_accs.append(train_model(data, n_classes=n_classes,
                                     epochs=epochs, verbose=False, seed=s).test_acc)
    full_acc = float(np.mean(full_accs))

    rows: list[AblationRow] = []
    for group_name, cols in FEATURE_GROUPS.items():
        ablated = _drop_features(features, cols)
        # Reuse the existing graph; just rebuild the PyG data with new x.
        accs = []
        for s in seeds:
            # Build a fresh graph with the ablated features.
            g_copy = nx.Graph()
            for n, attrs in graph.nodes(data=True):
                g_copy.add_node(n)
            for n in g_copy.nodes:
                idx = features.index.get_loc(n)
                g_copy.nodes[n]["x"] = ablated.values[idx].astype(np.float32)
            for u, v, data in graph.edges(data=True):
                g_copy.add_edge(u, v, **data)
            data = to_pyg(g_copy, labels)
            accs.append(train_model(data, n_classes=n_classes,
                                    epochs=epochs, verbose=False, seed=s).test_acc)
        acc = float(np.mean(accs))
        rows.append(AblationRow(component=f"-{group_name}", test_acc=acc,
                                delta=acc - full_acc))
    return full_acc, rows


def run_edge_ablation(
    features: pd.DataFrame,
    metadata: pd.DataFrame,
    flows: pd.DataFrame,
    signals: pd.DataFrame,
    labels: dict[str, int],
    *,
    n_classes: int = len(TEAMS),
    epochs: int = 200,
    seeds: list[int] = (1, 2, 3, 4, 5),
) -> tuple[float, list[AblationRow]]:
    """How much does each edge type contribute? Drop one type at a time.

    Rebuilds the graph from raw inputs each time — that's the only honest
    way to ablate an edge type, since edges that mix kinds shouldn't have
    their weights heuristically rescaled.
    """
    full_accs = []
    full_graph = build_graph(features, metadata, flows, signals,
                             edge_kinds=tuple(EDGE_KINDS))
    for s in seeds:
        data = to_pyg(full_graph, labels)
        full_accs.append(train_model(data, n_classes=n_classes,
                                     epochs=epochs, verbose=False, seed=s).test_acc)
    full_acc = float(np.mean(full_accs))

    rows: list[AblationRow] = []
    for kind in EDGE_KINDS:
        kept = tuple(k for k in EDGE_KINDS if k != kind)
        g_dropped = build_graph(features, metadata, flows, signals, edge_kinds=kept)
        if g_dropped.number_of_edges() == 0:
            rows.append(AblationRow(component=f"-{kind}_edges", test_acc=float("nan"),
                                    delta=float("nan")))
            continue
        accs = []
        for s in seeds:
            data = to_pyg(g_dropped, labels)
            accs.append(train_model(data, n_classes=n_classes,
                                    epochs=epochs, verbose=False, seed=s).test_acc)
        acc = float(np.mean(accs))
        rows.append(AblationRow(component=f"-{kind}_edges", test_acc=acc,
                                delta=acc - full_acc))
    return full_acc, rows
