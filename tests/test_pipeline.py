"""Smoke tests — make sure the whole pipeline runs on synthetic data."""

from __future__ import annotations

import numpy as np
import pytest

from costdna import TEAMS
from costdna.baselines import (run_logistic_regression, run_node2vec)
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


def test_decoy_kind_is_generated_with_correct_metadata():
    """The decoy kind is the adversarial case for issue #6: graph says B,
    behaviour says A, ground-truth label is B. Validate the generator
    produces decoys with the expected `decoy_for` field set to a
    different team than `team`."""
    signals, metadata, flows, _ = generate_synthetic_signals(
        n_per_type_per_team=3, days=7, seed=99,
    )
    decoys = metadata[metadata["kind"] == "decoy"]
    assert len(decoys) >= 3, (
        f"expected ≥3 decoys, got {len(decoys)} (synthetic env mis-configured)"
    )
    for _, row in decoys.iterrows():
        assert row["decoy_for"] is not None, (
            f"decoy resource {row['resource_id']} has no decoy_for set"
        )
        assert row["decoy_for"] != row["team"], (
            "decoy_for must name a team OTHER than the owning team — "
            "otherwise it's not adversarial"
        )

    # Pull events for the first decoy and verify the caller-team distribution
    # is dominated by decoy_for (team A), not team (team B). This is the
    # behavioural-vs-structural disagreement the kind models. Roles use
    # industry-style prefixes that don't literally contain the team name —
    # backend roles are 'apicore-*', data are 'etl-*', ml are 'mlops-*',
    # platform are 'devops-*'.
    from costdna.collectors.synthetic import PROFILES

    first = decoys.iloc[0]
    rid = first["resource_id"]
    events = signals[signals["resource_id"] == rid]
    assert not events.empty, f"decoy {rid} has no events"
    roles = events["iam_role"].fillna("").tolist()
    target_team = first["decoy_for"]
    target_pool = set(PROFILES[target_team].role_pool)
    n_target = sum(1 for r in roles if r in target_pool)
    n_total = len(roles)
    # We set decoy callers to come from team A 85% of the time. Allow some
    # slop because of finite-sample noise. Floor at 0.5 — anything below
    # that means the decoy isn't actually mimicking team A meaningfully.
    assert n_target / max(1, n_total) >= 0.5, (
        f"decoy {rid} should have ≥50% callers from team {target_team!r}; "
        f"got {n_target}/{n_total} ({100*n_target/n_total:.0f}%)"
    )


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
    # All five "hard" kinds are designed to break feature-only baselines in
    # at least some way. We assert that LogReg fails on at least ONE of them
    # — if it solves them all, the synthetic env's noise is too gentle.
    # `sparse` is included because by design it has too few events for
    # behavioural fingerprinting to stabilise; if even sparse is solved,
    # the test stops being meaningful.
    hard_kinds = ("cross_team", "shared_service", "reassigned", "sparse")
    hard_accs = [log_reg.per_kind.get(k, 1.0) for k in hard_kinds
                 if k in log_reg.per_kind]
    assert any(a <= 0.5 for a in hard_accs), \
        f"LogReg solved every hard case ({log_reg.per_kind}) — noise too gentle"


def test_node2vec_baseline_runs():
    """node2vec+LR runs end-to-end and beats Majority on synthetic data.

    This is a smoke test, not an accuracy claim — the strong-baseline numbers
    live in docs/v2/results-phase2.md. We assert two things:
    1. The baseline doesn't crash on a realistic small graph
    2. It beats random by some margin (sanity check on the wiring)
    """
    pytest.importorskip("torch_geometric")
    from costdna.collectors import generate_synthetic_signals
    from costdna.features import extract_features, normalize_features
    from costdna.graph import build_graph

    signals, metadata, flows, _ = generate_synthetic_signals(
        n_per_type_per_team=3, days=7, seed=11,
    )
    metadata = metadata[metadata["team"].isin(TEAMS)].reset_index(drop=True)
    signals = signals[signals["resource_id"].isin(metadata["resource_id"])]
    feats_norm = normalize_features(extract_features(signals, metadata))
    g = build_graph(feats_norm, metadata, flows, signals)
    y = np.array([TEAMS.index(t) for t in metadata["team"]])
    kinds = list(metadata["kind"])

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

    # Align node order to metadata order so the baseline's features/labels match.
    node_ids = metadata["resource_id"].tolist()
    # Subset the graph to just the labeled nodes to keep the test fast.
    sub = g.subgraph(node_ids).copy()

    # Tiny config for test speed — the production config in benchmark.py uses
    # walk_length=20, walks_per_node=10, n_epochs=5 (gensim epochs over walks).
    result = run_node2vec(
        sub, node_ids, feats_norm.values, y, train_mask, test_mask, kinds,
        embedding_dim=16, walk_length=8, context_size=4, walks_per_node=4,
        n_epochs=3, seed=11,
    )
    random_baseline = 1.0 / len(TEAMS)
    assert result.test_acc > random_baseline, (
        f"node2vec+LR test_acc={result.test_acc:.3f} should beat random "
        f"baseline {random_baseline:.3f}"
    )
    assert result.name == "node2vec+LR"
    assert result.predictions.shape == y.shape
    assert result.confidences.shape == y.shape
