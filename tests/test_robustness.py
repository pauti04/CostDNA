"""Tests for the robustness perturbations (label noise + edge dropout)."""

from __future__ import annotations

import numpy as np
import pytest

from costdna.robustness import drop_edges, inject_label_noise


def test_label_noise_zero_frac_is_noop():
    y = np.array([0, 1, 2, 3, 0, 1])
    rng = np.random.default_rng(0)
    out = inject_label_noise(y, np.arange(len(y)), 0.0, 4, rng)
    assert np.array_equal(out, y)


def test_label_noise_does_not_mutate_input():
    y = np.array([0, 1, 2, 3])
    rng = np.random.default_rng(0)
    _ = inject_label_noise(y, np.arange(4), 1.0, 4, rng)
    assert np.array_equal(y, [0, 1, 2, 3]), "input array must not be mutated"


def test_label_noise_full_frac_flips_all_to_wrong_class():
    y = np.array([0, 1, 2, 3] * 25)          # 100 labels, 4 classes
    rng = np.random.default_rng(1)
    out = inject_label_noise(y, np.arange(len(y)), 1.0, 4, rng)
    # Every corrupted label must differ from the original (never a no-op flip).
    assert np.all(out != y), "100% noise should change every eligible label"
    # All still valid classes.
    assert set(out.tolist()) <= {0, 1, 2, 3}


def test_label_noise_respects_fraction():
    y = np.zeros(100, dtype=int)
    rng = np.random.default_rng(2)
    out = inject_label_noise(y, np.arange(100), 0.30, 4, rng)
    n_changed = int((out != y).sum())
    assert n_changed == 30, f"expected 30 flips at frac=0.30, got {n_changed}"


def test_label_noise_only_touches_given_indices():
    y = np.zeros(100, dtype=int)
    rng = np.random.default_rng(3)
    train_idx = np.arange(0, 50)             # only first half eligible
    out = inject_label_noise(y, train_idx, 1.0, 4, rng)
    # Second half (the "test" labels) must be untouched.
    assert np.array_equal(out[50:], y[50:]), "labels outside `indices` must stay clean"
    assert np.all(out[:50] != 0), "all eligible labels should have flipped"


def test_label_noise_rejects_bad_frac():
    with pytest.raises(ValueError):
        inject_label_noise(np.array([0, 1]), np.arange(2), 1.5, 2, np.random.default_rng(0))


def test_drop_edges_keep_all():
    e = np.array([[0, 1, 2, 3], [1, 2, 3, 0]])
    out = drop_edges(e, 1.0, np.random.default_rng(0))
    assert out.shape == e.shape


def test_drop_edges_keep_half():
    e = np.array([[0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
                  [1, 2, 3, 4, 5, 6, 7, 8, 9, 0]])
    out = drop_edges(e, 0.5, np.random.default_rng(0))
    assert out.shape[1] == 5
    # Kept edges must be a subset of originals (columns preserved intact).
    kept = set(map(tuple, out.T.tolist()))
    orig = set(map(tuple, e.T.tolist()))
    assert kept <= orig


def test_drop_edges_keep_none_gives_empty_graph():
    e = np.array([[0, 1, 2], [1, 2, 0]])
    out = drop_edges(e, 0.0, np.random.default_rng(0))
    assert out.shape == (2, 0)


def test_drop_edges_rejects_bad_frac():
    with pytest.raises(ValueError):
        drop_edges(np.array([[0], [1]]), -0.1, np.random.default_rng(0))
