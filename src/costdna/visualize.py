"""Visualize the GraphSAGE embedding space.

Generates a 2D UMAP projection of the GNN's hidden representations colored
by team. Same-team resources should cluster together — visually confirms
that the embedding space encodes team membership.

Saves a PNG to the run directory; opens in any image viewer.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

log = logging.getLogger(__name__)


# Distinct, colorblind-aware palette. Cycled if more than 12 teams.
_PALETTE = [
    "#0173b2", "#de8f05", "#029e73", "#cc78bc", "#ca9161",
    "#fbafe4", "#949494", "#ece133", "#56b4e9", "#d55e00",
    "#000000", "#666666",
]


def render_umap(
    embeddings: np.ndarray,
    teams: list[str],
    output_path: Path,
    *,
    title: str = "GraphSAGE embedding space",
    n_neighbors: int = 15,
    min_dist: float = 0.1,
    seed: int = 42,
    figsize: tuple[float, float] = (10, 7),
    dpi: int = 140,
) -> None:
    """Project embeddings to 2D via UMAP and save a labeled scatter plot.

    Falls back to PCA if umap-learn isn't installed.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    try:
        import umap
        reducer = umap.UMAP(n_components=2, n_neighbors=n_neighbors,
                            min_dist=min_dist, random_state=seed)
        proj = reducer.fit_transform(embeddings)
        method = "UMAP"
    except ImportError:
        from sklearn.decomposition import PCA
        proj = PCA(n_components=2, random_state=seed).fit_transform(embeddings)
        method = "PCA"

    unique_teams = sorted(set(teams))
    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
    for i, team in enumerate(unique_teams):
        mask = [t == team for t in teams]
        idx = np.where(mask)[0]
        if len(idx) == 0:
            continue
        color = _PALETTE[i % len(_PALETTE)]
        # Truncate very long Azure subscription names for the legend.
        label = team if len(team) <= 28 else team[:25] + "…"
        ax.scatter(proj[idx, 0], proj[idx, 1], s=22, alpha=0.7,
                   c=color, label=label, edgecolors="white", linewidths=0.4)

    ax.set_title(f"{title} — {method} 2D projection",
                 fontsize=13, fontweight="bold")
    ax.set_xlabel(f"{method}-1"); ax.set_ylabel(f"{method}-2")
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5),
              fontsize=8, frameon=False, title="team")
    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, bbox_inches="tight")
    plt.close(fig)
    log.info("wrote %s (%s)", output_path, method)


def render_anomaly_scatter(
    embeddings: np.ndarray,
    teams: list[str],
    confidences: np.ndarray,
    output_path: Path,
    *,
    title: str = "Embedding space — confidence as size",
    seed: int = 42,
    figsize: tuple[float, float] = (10, 7),
    dpi: int = 140,
) -> None:
    """Same UMAP projection, but with marker size = confidence and a separate
    overlay for low-confidence (anomalous) points."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    try:
        import umap
        proj = umap.UMAP(n_components=2, random_state=seed).fit_transform(embeddings)
    except ImportError:
        from sklearn.decomposition import PCA
        proj = PCA(n_components=2, random_state=seed).fit_transform(embeddings)

    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
    unique_teams = sorted(set(teams))
    for i, team in enumerate(unique_teams):
        idx = np.where(np.array(teams) == team)[0]
        if len(idx) == 0:
            continue
        color = _PALETTE[i % len(_PALETTE)]
        ax.scatter(proj[idx, 0], proj[idx, 1],
                   s=10 + 50 * confidences[idx],
                   c=color, alpha=0.6, edgecolors="white", linewidths=0.3,
                   label=team[:25] + ("…" if len(team) > 25 else ""))

    # Highlight anomalies (confidence < 0.5).
    anom_idx = np.where(confidences < 0.5)[0]
    if len(anom_idx) > 0:
        ax.scatter(proj[anom_idx, 0], proj[anom_idx, 1],
                   s=80, marker="x", c="red", alpha=0.85,
                   linewidths=2, label=f"anomaly ({len(anom_idx)})")

    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.set_xlabel("UMAP-1"); ax.set_ylabel("UMAP-2")
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5),
              fontsize=8, frameon=False)
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches="tight")
    plt.close(fig)
    log.info("wrote %s", output_path)
