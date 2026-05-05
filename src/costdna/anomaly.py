"""Anomaly detection on the GNN's embedding space.

A resource that fits *no* team is the most interesting kind. It might be:
  - cryptojacking: a Lambda someone deployed via a leaked credential
  - a vendor's resource (e.g. a Datadog forwarder) with its own pattern
  - the seed of a new team forming
  - or just a weird one-off — but you want a human to look at it

Method:
  1. Compute the centroid of each team's embeddings (using TRAIN labels only,
     so we don't peek at test labels).
  2. For every resource, take the distance to its NEAREST centroid.
  3. Within each predicted team, z-score those distances. A high z-score
     means "even among my team, this one is far from the cluster center."
  4. Combine with prediction confidence: low confidence + high distance =
     strong anomaly.

Output: ranked list, ready for the operator.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class Anomaly:
    resource_id: str
    predicted_team: str
    confidence: float
    centroid_distance: float
    z_score: float        # within predicted team
    score: float          # combined: lower confidence + higher z = larger
    reason: str           # human-readable summary


def _nearest_centroid_distance(emb: np.ndarray,
                               centroids: dict[int, np.ndarray]) -> tuple[int, float]:
    best_team, best_dist = -1, float("inf")
    for team_idx, c in centroids.items():
        d = float(np.linalg.norm(emb - c))
        if d < best_dist:
            best_team, best_dist = team_idx, d
    return best_team, best_dist


def find_anomalies(
    embeddings: np.ndarray,
    predictions: np.ndarray,
    confidences: np.ndarray,
    node_ids: list[str],
    train_labels: np.ndarray,
    train_mask: np.ndarray,
    teams: tuple[str, ...],
    *,
    confidence_threshold: float = 0.6,
    z_threshold: float = 1.5,
    graph=None,
) -> list[Anomaly]:
    """Returns anomalies sorted most-suspicious first.

    Three independent signals — a resource fires the anomaly flag when any
    combination is strong enough:

      1. Low prediction confidence      (model is torn)
      2. Far from team centroid (z > τ) (outlier within its team)
      3. Few graph neighbors            (no IAM/VPC/network ties — orphan-like)

    The combined score weights all three.
    """
    centroids: dict[int, np.ndarray] = {}
    for c in range(len(teams)):
        idx = (train_labels == c) & train_mask
        if idx.sum() == 0:
            continue
        centroids[c] = embeddings[idx].mean(axis=0)

    if not centroids:
        return []

    nearest_team = np.zeros(len(embeddings), dtype=int)
    centroid_dist = np.zeros(len(embeddings))
    for i, e in enumerate(embeddings):
        nt, d = _nearest_centroid_distance(e, centroids)
        nearest_team[i] = nt
        centroid_dist[i] = d

    # Per-team z-scores so a "far" cluster isn't penalized in absolute terms.
    z_scores = np.zeros(len(embeddings))
    for c in range(len(teams)):
        team_idx = predictions == c
        if not team_idx.any():
            continue
        mu = centroid_dist[team_idx].mean()
        sigma = centroid_dist[team_idx].std() + 1e-9
        z_scores[team_idx] = (centroid_dist[team_idx] - mu) / sigma

    # Graph-isolation signal: low degree = few connections = suspicious.
    degrees = np.zeros(len(embeddings))
    if graph is not None:
        node_to_idx = {n: i for i, n in enumerate(node_ids)}
        for n in graph.nodes:
            i = node_to_idx.get(n)
            if i is not None:
                degrees[i] = graph.degree(n)
        # Z-score the degree (low degree = positive isolation_z).
        if degrees.std() > 0:
            isolation_z = (degrees.mean() - degrees) / (degrees.std() + 1e-9)
        else:
            isolation_z = np.zeros_like(degrees)
    else:
        isolation_z = np.zeros(len(embeddings))

    anomalies: list[Anomaly] = []
    for i in range(len(embeddings)):
        low_conf = confidences[i] < confidence_threshold
        far_outlier = z_scores[i] > z_threshold
        isolated = isolation_z[i] > 1.0

        if not (low_conf or far_outlier or isolated):
            continue

        reason_parts = []
        if low_conf:
            reason_parts.append(f"low confidence ({confidences[i]:.2f})")
        if far_outlier:
            reason_parts.append(
                f"{z_scores[i]:.1f}σ from {teams[predictions[i]]} centroid")
        if isolated:
            reason_parts.append(f"only {int(degrees[i])} graph neighbors")
        # Combined score weights all three signals.
        score = ((1 - confidences[i])
                 + max(0.0, z_scores[i]) * 0.3
                 + max(0.0, isolation_z[i]) * 0.5)

        anomalies.append(Anomaly(
            resource_id=node_ids[i],
            predicted_team=teams[predictions[i]],
            confidence=float(confidences[i]),
            centroid_distance=float(centroid_dist[i]),
            z_score=float(z_scores[i]),
            score=float(score),
            reason=" + ".join(reason_parts),
        ))

    anomalies.sort(key=lambda a: -a.score)
    return anomalies
