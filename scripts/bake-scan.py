"""Generate a synthetic scan and dump as JSON for the live web demo.

Output: web/public/data/scan.json — single file containing predictions,
metadata, signals (subset), deploys. Loaded by the /api/ask route at
cold start so the LLM agent has something to query.

Run via:  scripts/bake-scan.py
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pandas as pd

from costdna import TEAMS
from costdna.collectors import generate_synthetic_signals
from costdna.features import extract_features, normalize_features
from costdna.graph import build_graph, to_pyg
from costdna.semantic import (extract_semantic_features,
                               extract_signal_explanations)
from costdna.train import train_model


def main() -> None:
    print("→ generating synthetic scan…")
    signals, metadata, flows, deploys = generate_synthetic_signals(
        n_per_type_per_team=3, days=14, seed=42,
    )
    feats = normalize_features(extract_features(signals, metadata))
    sem = extract_semantic_features(metadata, project_to=32)
    feats = pd.concat([feats, sem.reindex(feats.index).fillna(0.0)], axis=1)
    graph = build_graph(feats, metadata, flows, signals)

    team_idx = {t: i for i, t in enumerate(TEAMS)}
    labels = {row["resource_id"]: team_idx[row["team"]]
              for _, row in metadata.iterrows() if row["team"] in TEAMS}
    data = to_pyg(graph, labels)
    print("→ training GraphSAGE…")
    result = train_model(data, n_classes=len(TEAMS), epochs=200, verbose=False, seed=42)

    pred_team = [TEAMS[int(p)] if 0 <= int(p) < len(TEAMS) else "unknown"
                 for p in result.predictions]

    pred_df = pd.DataFrame({
        "resource_id": data.node_ids,
        "team_pred": pred_team,
        "confidence": [float(c) for c in result.confidences],
    }).merge(
        metadata[["resource_id", "resource_type", "team", "kind"]],
        on="resource_id", how="left",
    ).rename(columns={"team": "team_truth"})

    expl = extract_signal_explanations(metadata, pred_team)
    pred_df = pred_df.merge(expl, on="resource_id", how="left")

    # Trim signals to keep the JSON manageable.
    cost_signals = signals[signals["signal_type"] == "cost"].copy()
    event_signals = signals[signals["signal_type"] == "cloudtrail_event"].copy()
    # Keep first 100 events per resource for the agent's signal_history tool.
    event_signals = (event_signals.sort_values("timestamp")
                                  .groupby("resource_id").head(100))
    trimmed_signals = pd.concat([cost_signals, event_signals], ignore_index=True)
    trimmed_signals["timestamp"] = trimmed_signals["timestamp"].astype(str)

    deploys_clean = deploys.copy()
    deploys_clean["timestamp"] = deploys_clean["timestamp"].astype(str)

    out = {
        "predictions": pred_df.to_dict("records"),
        "metadata":    metadata.to_dict("records"),
        "signals":     trimmed_signals.to_dict("records"),
        "deploys":     deploys_clean.to_dict("records"),
        "teams":       sorted(set(pred_team)),
        "summary": {
            "total_resources":   int(len(pred_df)),
            "total_signal_rows": int(len(trimmed_signals)),
            "n_teams":           len(set(pred_team)),
            "model_test_acc":    float(result.test_acc),
        },
    }

    def _strict(o):
        if isinstance(o, dict):
            return {k: _strict(v) for k, v in o.items()}
        if isinstance(o, list):
            return [_strict(v) for v in o]
        if isinstance(o, float) and (math.isnan(o) or math.isinf(o)):
            return None
        return o

    out_path = Path("web/public/data/scan.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(_strict(out), default=str, allow_nan=False))
    size_mb = out_path.stat().st_size / 1024 / 1024
    print(f"→ wrote {out_path} ({size_mb:.1f} MB, "
          f"{len(out['predictions'])} resources, "
          f"{len(out['signals']):,} signals)")


if __name__ == "__main__":
    main()
