"""Streamlit UI for CostDNA.

Run with:  streamlit run -m costdna.webapp
Or:        costdna serve   (after wiring into cli.py)

The intent: FinOps engineers without CLI comfort can still:
  1. Upload a previously-saved scan dir (or run synthetic)
  2. Browse predictions with confidence + explanation
  3. Filter by team, by confidence, by resource type
  4. Click "approve" on a row to add it to a tag-application list
  5. Export the approved list as a CSV or `aws` CLI commands
"""

from __future__ import annotations

import io
from pathlib import Path

import pandas as pd
import streamlit as st


def _human_money(x: float) -> str:
    return f"${x:,.2f}"


def main() -> None:
    st.set_page_config(page_title="CostDNA", page_icon="💸", layout="wide")

    st.title("CostDNA")
    st.caption(
        "Behavioral + semantic GNN attribution for AWS resources. "
        "Upload a saved scan or run the synthetic demo to explore predictions."
    )

    with st.sidebar:
        st.header("Source")
        source = st.radio(
            "Where do predictions come from?",
            options=["Saved scan directory", "Run synthetic now"],
            index=0,
        )

        df: pd.DataFrame | None = None
        signals: pd.DataFrame | None = None
        metadata: pd.DataFrame | None = None

        if source == "Saved scan directory":
            uploaded = st.file_uploader(
                "Upload predictions.csv", type=["csv"], accept_multiple_files=False,
            )
            if uploaded is not None:
                df = pd.read_csv(uploaded)
            else:
                # Default: try to load from runs/ if running locally.
                default_path = Path("runs/azure-2/predictions.csv")
                if default_path.exists():
                    if st.button(f"Load demo: {default_path}"):
                        df = pd.read_csv(default_path)
        else:
            if st.button("Run synthetic scan", type="primary"):
                with st.spinner("Generating synthetic AWS env + training GraphSAGE…"):
                    from costdna import TEAMS
                    from costdna.collectors import generate_synthetic_signals
                    from costdna.features import (extract_features,
                                                   normalize_features)
                    from costdna.graph import build_graph, to_pyg
                    from costdna.semantic import (extract_semantic_features,
                                                   extract_signal_explanations)
                    from costdna.train import train_model

                    signals, metadata, flows, _ = generate_synthetic_signals(
                        n_per_type_per_team=3, days=14, seed=42,
                    )
                    feats = normalize_features(extract_features(signals, metadata))
                    sem = extract_semantic_features(metadata, project_to=32)
                    feats = pd.concat(
                        [feats, sem.reindex(feats.index).fillna(0.0)], axis=1,
                    )
                    g = build_graph(feats, metadata, flows, signals)
                    team_idx = {t: i for i, t in enumerate(TEAMS)}
                    labels = {
                        r["resource_id"]: team_idx[r["team"]]
                        for _, r in metadata.iterrows() if r["team"] in TEAMS
                    }
                    data = to_pyg(g, labels)
                    result = train_model(data, n_classes=len(TEAMS),
                                          epochs=200, verbose=False, seed=42)

                    pred_team = [TEAMS[int(p)] if 0 <= int(p) < len(TEAMS)
                                 else "unknown" for p in result.predictions]
                    df = pd.DataFrame({
                        "resource_id": data.node_ids,
                        "team_pred": pred_team,
                        "confidence": result.confidences,
                    }).merge(
                        metadata[["resource_id", "resource_type", "team", "kind"]],
                        on="resource_id", how="left",
                    ).rename(columns={"team": "team_truth"})
                    expl = extract_signal_explanations(metadata, pred_team)
                    df = df.merge(expl, on="resource_id", how="left")

    if df is None or df.empty:
        st.info(
            "👈 Pick a source on the left. "
            "Easiest: \"Run synthetic now\" → click the button.",
        )
        return

    # ---- Top-level metrics ----
    cols = st.columns(4)
    n_total = len(df)
    high_conf = (df["confidence"] >= 0.7).sum()
    review = (df["confidence"] < 0.7).sum()
    if "team_truth" in df.columns:
        accuracy = (df["team_pred"] == df["team_truth"]).mean()
    else:
        accuracy = None

    cols[0].metric("Resources", n_total)
    cols[1].metric("Ready to tag (≥0.7)", high_conf,
                   delta=f"{high_conf / max(1, n_total) * 100:.0f}%")
    cols[2].metric("Need review (<0.7)", review,
                   delta=f"{review / max(1, n_total) * 100:.0f}%",
                   delta_color="inverse")
    if accuracy is not None:
        cols[3].metric("Accuracy vs truth", f"{accuracy * 100:.1f}%")
    else:
        cols[3].metric("Predicted teams",
                       df["team_pred"].nunique() if "team_pred" in df.columns else 0)

    st.divider()

    # ---- Per-team breakdown ----
    if "team_pred" in df.columns:
        st.subheader("Per-team breakdown")
        team_counts = (df.groupby("team_pred")
                         .agg(n=("resource_id", "count"),
                              avg_conf=("confidence", "mean"))
                         .sort_values("n", ascending=False))
        team_counts["avg_conf"] = (team_counts["avg_conf"] * 100).round(1)
        st.dataframe(team_counts, use_container_width=True)

    # ---- Filters + sortable table ----
    st.subheader("Predictions")
    f1, f2, f3 = st.columns([2, 2, 2])
    with f1:
        team_filter = st.multiselect(
            "Team", sorted(df["team_pred"].unique()) if "team_pred" in df.columns else [],
            default=[],
        )
    with f2:
        type_filter = st.multiselect(
            "Resource type",
            sorted(df["resource_type"].dropna().unique())
                if "resource_type" in df.columns else [],
            default=[],
        )
    with f3:
        min_conf = st.slider("Min confidence", 0.0, 1.0, 0.0, 0.05)

    view = df.copy()
    if team_filter:
        view = view[view["team_pred"].isin(team_filter)]
    if type_filter:
        view = view[view["resource_type"].isin(type_filter)]
    view = view[view["confidence"] >= min_conf]
    view = view.sort_values("confidence", ascending=False)

    # Pretty columns.
    show_cols = ["resource_id", "resource_type", "team_pred", "confidence", "explanation"]
    show_cols = [c for c in show_cols if c in view.columns]
    if "team_truth" in view.columns:
        show_cols.insert(3, "team_truth")
    st.dataframe(
        view[show_cols].style.format({"confidence": "{:.2f}"}),
        use_container_width=True,
        height=520,
    )

    # ---- Export ----
    st.subheader("Export")
    csv_buf = io.StringIO()
    view.to_csv(csv_buf, index=False)
    st.download_button(
        "📥 Download filtered predictions.csv",
        data=csv_buf.getvalue(),
        file_name="predictions.csv",
        mime="text/csv",
    )

    # ---- AWS CLI tag commands ----
    st.subheader("Generate `aws` tag commands")
    threshold = st.slider("Apply tags only at confidence ≥", 0.0, 1.0, 0.7, 0.05,
                          key="apply_threshold")
    apply_view = view[view["confidence"] >= threshold]
    if len(apply_view) == 0:
        st.warning("No resources above the chosen confidence threshold.")
    else:
        from costdna.tagger import build_tag_ops
        ops = build_tag_ops(apply_view, min_confidence=threshold)
        cmds = "\n".join(op.cli_command for op in ops)
        st.code(cmds, language="bash")
        st.caption(
            f"{len(ops)} commands generated. Pipe to `bash` to apply, "
            "or use `costdna apply --apply` from the CLI for direct boto3 calls."
        )


if __name__ == "__main__":
    main()
