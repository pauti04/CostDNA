"""Semantic feature extraction.

The signal that exists in real cloud accounts but we previously ignored:
IAM role names, resource names, existing partial tags. Real names like
`prod-data-etl-runner-role` literally hint at the team.

We embed each resource's name-like text fields with a small sentence-transformer,
then expose the embedding as additional features. On real accounts, this is
typically the dominant signal — IAM role naming conventions are the strongest
team signal most accounts have.

Why sentence-transformers and not the OpenAI/Anthropic API:
- Free, no API key, works offline
- ~80MB model, runs on CPU in milliseconds
- Good enough for naming-convention semantics

The model is loaded lazily on first call.
"""

from __future__ import annotations

import logging
from functools import lru_cache

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def _model(name: str = DEFAULT_MODEL):
    """Load the sentence-transformer model. Cached after first call."""
    from sentence_transformers import SentenceTransformer
    log.info("loading sentence-transformer %s", name)
    return SentenceTransformer(name)


def _row_to_text(row: pd.Series) -> str:
    """Build the text representation of one resource for embedding.

    We deliberately concatenate everything name-like with separators that
    sentence-transformers tokenize cleanly. The order matters less than the
    content — same-team resources share substrings (the team's tribe name,
    purpose, environment) and the embedding model picks those up.
    """
    parts = []
    if row.get("resource_id"):
        parts.append(str(row["resource_id"]))
    if row.get("resource_type"):
        parts.append(f"type={row['resource_type']}")
    if row.get("iam_role"):
        # Strip ARN prefix if present — keep just the role name.
        role = str(row["iam_role"]).split("/")[-1]
        parts.append(f"role={role}")
    if row.get("vpc_cidr"):
        parts.append(f"vpc={row['vpc_cidr']}")
    # Optional pre-existing tags (stored as a dict in metadata if available).
    tags = row.get("tags") or {}
    if isinstance(tags, dict) and tags:
        parts.extend(f"{k}={v}" for k, v in tags.items())
    return " | ".join(parts)


def extract_semantic_features(
    metadata: pd.DataFrame,
    *,
    model_name: str = DEFAULT_MODEL,
    project_to: int | None = 32,
    seed: int = 42,
) -> pd.DataFrame:
    """Returns one row per resource, indexed by resource_id, with embedding columns.

    `project_to` projects the (typically 384-dim) embedding down to a smaller
    feature space via PCA so the GNN's input layer doesn't explode. Set to
    None to keep the full embedding.

    On a typical 100-resource account this runs in <2 seconds on CPU.
    """
    if metadata.empty:
        return pd.DataFrame()

    texts = [_row_to_text(row) for _, row in metadata.iterrows()]
    log.info("encoding %d resources with %s", len(texts), model_name)
    model = _model(model_name)
    emb = model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
    emb = np.asarray(emb, dtype=np.float32)

    if project_to is not None and emb.shape[1] > project_to and len(texts) > project_to:
        from sklearn.decomposition import PCA
        pca = PCA(n_components=project_to, random_state=seed)
        emb = pca.fit_transform(emb).astype(np.float32)
        log.info("projected embedding %d -> %d via PCA", model.get_sentence_embedding_dimension(),
                 project_to)

    cols = [f"sem_{i:03d}" for i in range(emb.shape[1])]
    return pd.DataFrame(emb, columns=cols, index=metadata["resource_id"].values)


def extract_signal_explanations(
    metadata: pd.DataFrame,
    predictions_team: list[str],
) -> pd.DataFrame:
    """Per-resource human-readable explanation of why a team was assigned.

    Looks at name-like fields and surfaces substring overlap with the predicted
    team name. Crude but useful for "why did you pick this?" on a CSV row.
    """
    rows = []
    for (_, r), team in zip(metadata.iterrows(), predictions_team):
        signals: list[str] = []
        team_lc = team.lower()
        for field in ("iam_role", "resource_id", "vpc_cidr"):
            v = str(r.get(field, "")).lower()
            if not v or v == "nan":
                continue
            # Quick substring tells: team token appears in field.
            for tok in team_lc.replace("-", " ").replace("_", " ").split():
                if len(tok) >= 3 and tok in v:
                    signals.append(f"{field} contains '{tok}'")
                    break
        tags = r.get("tags") or {}
        if isinstance(tags, dict):
            for k, v in tags.items():
                if team_lc in str(v).lower() or team_lc in str(k).lower():
                    signals.append(f"tag {k}={v} matches team")
                    break
        rows.append({
            "resource_id": r["resource_id"],
            "explanation": "; ".join(signals) if signals
                           else "no name-based hint — relies on behavioral/graph signal",
        })
    return pd.DataFrame(rows)
