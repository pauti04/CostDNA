"""Smoke tests — make sure the whole pipeline runs on synthetic data."""

from __future__ import annotations

import numpy as np
import pytest

from costdna import TEAMS
from costdna.baselines import (majority_baseline, run_knn,
                               run_label_propagation, run_logistic_regression)
from costdna.collectors import generate_synthetic_signals
from costdna.features import FEATURE_COLUMNS, extract_features, normalize_features
from costdna.graph import build_graph, to_pyg


def test_synthetic_generator_shapes():
    signals, metadata, flows, deploys = generate_synthetic_signals(
        n_per_type_per_team=2, days=3, seed=1,
    )
    # Clean per-team resources + a fixed number of hard-case resources.
    assert len(metadata) >= len(TEAMS) * 4 * 2
    assert "kind" in metadata.columns
    assert set(metadata["kind"].unique()) >= {"clean", "shared_service",
                                              "reassigned", "sparse", "cross_team"}
    assert not signals.empty
    assert {"resource_id", "signal_type", "value", "timestamp"} <= set(signals.columns)
    assert not flows.empty
    assert not deploys.empty


def test_feature_extraction_columns():
    signals, metadata, _, _ = generate_synthetic_signals(n_per_type_per_team=1, days=2, seed=0)
    feats = extract_features(signals, metadata)
    assert list(feats.columns) == list(FEATURE_COLUMNS)
    assert (feats.index == metadata["resource_id"]).all()


def test_graph_has_intra_team_clustering():
    """Same-team resources should be connected, even with weak signal density."""
    signals, metadata, flows, _ = generate_synthetic_signals(
        n_per_type_per_team=2, days=3, seed=2,
    )
    feats = normalize_features(extract_features(signals, metadata))
    g = build_graph(feats, metadata, flows, signals)
    assert g.number_of_nodes() == len(metadata)
    assert g.number_of_edges() > 0


@pytest.mark.parametrize("epochs", [50])
def test_train_runs_and_beats_random(epochs):
    pytest.importorskip("torch_geometric")
    from costdna.train import train_model

    signals, metadata, flows, _ = generate_synthetic_signals(
        n_per_type_per_team=4, days=7, seed=5,
    )
    feats = normalize_features(extract_features(signals, metadata))
    g = build_graph(feats, metadata, flows, signals)
    labels = {row["resource_id"]: TEAMS.index(row["team"])
              for _, row in metadata.iterrows()
              if row["team"] in TEAMS}
    data = to_pyg(g, labels)
    result = train_model(data, n_classes=len(TEAMS),
                         epochs=epochs, verbose=False, seed=5)
    baseline = 1.0 / len(TEAMS)
    assert result.test_acc > 2 * baseline, \
        f"test_acc={result.test_acc:.3f} — signal too weak (baseline={baseline:.3f})"


def test_baselines_fail_on_hard_cases_features_only():
    """LogReg/k-NN should solve clean cases but fail on cross_team — that's
    the whole reason we need the GNN."""
    signals, metadata, flows, _ = generate_synthetic_signals(
        n_per_type_per_team=3, days=14, seed=42,
    )
    # Filter to only labeled (owned) resources.
    metadata = metadata[metadata["team"].isin(TEAMS)].reset_index(drop=True)
    signals = signals[signals["resource_id"].isin(metadata["resource_id"])]

    feats_norm = normalize_features(extract_features(signals, metadata))
    y = np.array([TEAMS.index(t) for t in metadata["team"]])
    kinds = list(metadata["kind"])

    # Stratified 70/30 split.
    rng = np.random.default_rng(0)
    train_mask = np.zeros(len(metadata), dtype=bool)
    test_mask = np.zeros(len(metadata), dtype=bool)
    by_kind: dict[str, list[int]] = {}
    for i, k in enumerate(kinds):
        by_kind.setdefault(k, []).append(i)
    for k, members in by_kind.items():
        rng.shuffle(members)
        cut = max(1, int(len(members) * 0.7))
        train_mask[members[:cut]] = True
        if len(members) > cut:
            test_mask[members[cut:]] = True

    log_reg = run_logistic_regression(feats_norm.values, y, train_mask, test_mask, kinds)
    hard_kinds = ("cross_team", "shared_service", "reassigned")
    hard_accs = [log_reg.per_kind.get(k, 1.0) for k in hard_kinds
                 if k in log_reg.per_kind]
    # At least ONE hard kind should be ≤50% — that's the whole point of having
    # them. If LogReg solves all of them, the synthetic noise is too gentle and
    # the GNN can't earn its keep.
    assert any(a <= 0.5 for a in hard_accs), \
        f"LogReg solved every hard case ({log_reg.per_kind}) — noise too gentle"
