"""CostDNA command-line interface.

Operational commands (the actual product):
  costdna doctor     — preflight: catch every reason a real-AWS run will fail
  costdna scan       — pipeline + exec summary + attribution + anomalies + spikes
  costdna apply      — write predicted teams back to AWS as tags (--dry-run default)
  costdna diff       — drift detection: compare two saved scans

Research / analysis commands:
  costdna benchmark  — multi-seed (--seeds N) or k-fold (--kfold K) comparison
  costdna ablate     — feature & edge ablation
  costdna calibrate  — confidence reliability diagram + ECE
  costdna learn      — active-learning curve

  costdna inspect    — re-run on previously-saved CSVs
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import click
import numpy as np
import pandas as pd
from rich.console import Console

from costdna import TEAMS
from costdna.ablate import run_edge_ablation, run_feature_ablation
from costdna.active import active_learning_loop
from costdna.anomaly import find_anomalies
from costdna.benchmark import (attributed_dollars, run_benchmark,
                               run_benchmark_kfold, run_benchmark_multiseed)
from costdna.calibrate import calibration_curve
from costdna.collectors import (collect_aws_signals, generate_synthetic_signals,
                                load_azure_trace)
from costdna.discover import discover_teams
from costdna.drift import compute_drift
from costdna.explain import explain_top_spikes
from costdna.features import extract_features, normalize_features
from costdna.graph import build_graph, to_pyg
from costdna.output import (render_ablation, render_anomalies,
                            render_attribution, render_benchmark,
                            render_calibration, render_confusion,
                            render_dollars, render_executive_summary,
                            render_explanations, render_learning_curve,
                            render_metrics, render_multiseed_benchmark)
from costdna.summary import build_summary
from costdna.tagger import apply_tags_live, build_tag_ops
from costdna.train import train_model

console = Console()


def _team_to_idx(team: str) -> int:
    return TEAMS.index(team)


def _idx_to_team(idx: int) -> str:
    return TEAMS[idx] if 0 <= idx < len(TEAMS) else "unknown"


def _effective_teams(metadata: pd.DataFrame) -> tuple[str, ...]:
    """Return the canonical TEAMS if the metadata uses them, otherwise derive
    teams from the data (e.g. Azure subscription IDs). Always sorted for
    determinism."""
    if "team" not in metadata.columns:
        return TEAMS
    present = sorted(metadata["team"].dropna().astype(str).unique())
    if all(t in TEAMS for t in present):
        return TEAMS
    return tuple(present)


def _load(synthetic: bool, aws_profile, region, days, seed,
          azure_trace: Path | None = None,
          azure_top_n: int = 25, azure_max_per_sub: int = 200,
          azure_readings: Path | None = None,
          cloud: str = "aws"):
    if azure_trace is not None:
        suffix = " + real CPU readings" if azure_readings else " (summary stats only)"
        console.print(f"[bold cyan]→[/] Loading Microsoft Azure public dataset "
                      f"from [bold]{azure_trace}[/]{suffix} "
                      f"(top {azure_top_n} subs × up to {azure_max_per_sub} VMs)")
        return load_azure_trace(azure_trace, days=days, seed=seed,
                                top_n_subscriptions=azure_top_n,
                                max_vms_per_sub=azure_max_per_sub,
                                readings_path=azure_readings)
    if synthetic:
        console.print(f"[bold cyan]→[/] Generating synthetic signals "
                      f"(seed={seed}, days={days}, with hard cases)")
        return generate_synthetic_signals(n_per_type_per_team=3, days=days, seed=seed)

    # Live cloud scan — multi-cloud dispatch via the CloudProvider registry.
    # `--cloud aws` (default) keeps the original AWS path; `--cloud azure`
    # and `--cloud gcp` use the live collectors in `collectors/azure_live.py`
    # and `collectors/gcp.py` (Azure interprets `region` as subscription_id;
    # GCP interprets `region` as project_id — see those modules' docstrings).
    if cloud == "aws":
        console.print(f"[bold cyan]→[/] Collecting from AWS "
                      f"(profile={aws_profile or 'default'}, region={region}, days={days})")
        # Pass our well-known simulator role names so the CloudTrail Username
        # sweep finds events made by team principals even when they don't show
        # up in EC2/RDS/Lambda metadata.
        extra_usernames = []
        try:
            from simulation.common import TEAM_ROLE
            extra_usernames = list(TEAM_ROLE.values())
        except ImportError:
            pass
        return collect_aws_signals(profile=aws_profile, region=region, days=days,
                                    extra_usernames=extra_usernames)

    # Multi-cloud path (Azure / GCP).
    from costdna.collectors._base import get_provider
    provider = get_provider(cloud)
    console.print(f"[bold cyan]→[/] Collecting from [bold]{cloud}[/] "
                  f"(scope={region}, days={days})")
    if cloud in ("azure", "gcp"):
        console.print(
            f"[yellow]⚠ {cloud} live collector is untested against a "
            f"production account — see src/costdna/collectors/{cloud}*.py "
            f"for status.[/]"
        )
    result = provider.collect(profile=aws_profile, region=region, days=days)
    return result.signals, result.metadata, result.flows, result.deploys


def _prepare(signals, metadata, flows):
    return _prepare_with_teams(signals, metadata, flows, TEAMS)


def _prepare_with_teams(signals, metadata, flows, teams: tuple[str, ...],
                        use_semantic: bool = True):
    """Build features (behavioral + optionally semantic), graph, and labels.

    With `use_semantic=True` (default), each resource's name-like fields
    (iam_role, resource_id, partial tags) are LLM-embedded and concatenated
    with the 9 behavioral features. On real accounts where IAM role names
    are semantic ("prod-data-etl-runner"), this is the dominant signal.
    """
    features = extract_features(signals, metadata)
    features_norm = normalize_features(features)

    if use_semantic and len(metadata) > 0:
        from costdna.semantic import extract_semantic_features
        sem = extract_semantic_features(metadata, project_to=32)
        if not sem.empty:
            sem_aligned = sem.reindex(features_norm.index).fillna(0.0)
            features_norm = pd.concat([features_norm, sem_aligned], axis=1)

    graph = build_graph(features_norm, metadata, flows, signals)
    labels: dict[str, int] = {}
    if "team" in metadata.columns:
        team_idx = {t: i for i, t in enumerate(teams)}
        for _, row in metadata.iterrows():
            team = row["team"]
            if team in team_idx:
                labels[row["resource_id"]] = team_idx[team]
    return features, features_norm, graph, labels


@click.group()
@click.version_option()
def main() -> None:
    """CostDNA — behavioral fingerprinting for AWS cost attribution."""


@main.command()
@click.option("--cloud",
              type=click.Choice(["aws", "azure", "gcp"], case_sensitive=False),
              default="aws", show_default=True,
              help="Which cloud to scan. AWS is production-tested; Azure and "
                   "GCP collectors are implemented per official SDK patterns "
                   "but untested against a live account — see "
                   "src/costdna/collectors/{azure_live,gcp}.py for status.")
@click.option("--aws-profile", default=None)
@click.option("--region", default="us-east-1", show_default=True,
              help="AWS region, OR Azure subscription_id, OR GCP project_id "
                   "(billing/audit scope depends on --cloud).")
@click.option("--days", default=14, show_default=True)
@click.option("--synthetic/--live", default=None)
@click.option("--seed", default=42, show_default=True)
@click.option("--epochs", default=200, show_default=True)
@click.option("--save-dir", type=click.Path(file_okay=False, path_type=Path), default=None)
@click.option("--show-truth", is_flag=True)
@click.option("--show-kind", is_flag=True, help="Show resource kind (clean / shared-svc / etc).")
@click.option("--labels", "labels_path",
              type=click.Path(exists=True, dir_okay=False, path_type=Path),
              default=None,
              help="CSV with columns resource_id,team — merged into metadata. "
                   "For real-AWS runs, point at terraform/labels.csv.")
@click.option("--azure-trace", "azure_trace",
              type=click.Path(exists=True, dir_okay=False, path_type=Path),
              default=None,
              help="Path to Microsoft Azure Public Dataset vmtable.csv(.gz). "
                   "Validates the methodology on 2.6M real cloud resources.")
@click.option("--azure-top-n", default=25, show_default=True,
              help="Top-N subscriptions to sample from Azure data.")
@click.option("--azure-max-per-sub", default=200, show_default=True,
              help="Max VMs per Azure subscription.")
@click.option("--azure-readings", "azure_readings",
              type=click.Path(exists=True, dir_okay=False, path_type=Path),
              default=None,
              help="Optional vm_cpu_readings file. Uses real per-VM time-series "
                   "instead of synthesizing from summary stats.")
@click.option("--save-umap", is_flag=True,
              help="Save a 2D UMAP plot of GraphSAGE embeddings (requires --save-dir).")
def scan(cloud, aws_profile, region, days, synthetic, seed, epochs, save_dir,
         show_truth, show_kind, labels_path, azure_trace,
         azure_top_n, azure_max_per_sub, save_umap, azure_readings):
    """Run the full pipeline: collect → features → graph → train → attribute → explain."""
    if azure_trace is not None:
        synthetic = False
    elif synthetic is None:
        synthetic = aws_profile is None and cloud == "aws"
    signals, metadata, flows, deploys = _load(
        synthetic, aws_profile, region, days, seed,
        azure_trace=azure_trace,
        azure_top_n=azure_top_n, azure_max_per_sub=azure_max_per_sub,
        azure_readings=azure_readings,
        cloud=cloud,
    )
    if metadata.empty:
        console.print("[red]No resources found.[/]")
        sys.exit(1)
    console.print(f"  loaded {len(metadata)} resources, {len(signals):,} signal rows, "
                  f"{len(flows)} flow edges, {len(deploys)} deploys")

    # Optionally merge external labels (e.g. from Terraform's labels.csv).
    if labels_path is not None:
        ext = pd.read_csv(labels_path)
        if "team" not in ext.columns or "resource_id" not in ext.columns:
            console.print(f"[red]{labels_path} must have columns "
                          "'resource_id' and 'team'.[/]")
            sys.exit(1)
        if "team" in metadata.columns:
            metadata = metadata.drop(columns=["team"])
        metadata = metadata.merge(ext[["resource_id", "team"]],
                                  on="resource_id", how="left")
        n_labeled = metadata["team"].notna().sum()
        console.print(f"  merged {n_labeled} labels from [bold]{labels_path}[/]")

    # Derive the active team list. For AWS this is just TEAMS; for Azure it's
    # the actual subscription IDs that appear in the data.
    active_teams = _effective_teams(metadata)
    if active_teams != TEAMS:
        console.print(f"  using {len(active_teams)} teams from data: "
                      f"{', '.join(active_teams[:5])}"
                      f"{' …' if len(active_teams) > 5 else ''}")

    features, features_norm, graph, labels = _prepare_with_teams(
        signals, metadata, flows, active_teams)
    console.print(f"  graph: {graph.number_of_nodes()} nodes, "
                  f"{graph.number_of_edges()} edges")
    if not labels:
        console.print("[yellow]⚠ No ground-truth labels in metadata.[/]")
        console.print("[bold cyan]→[/] Auto-discovering teams from IAM role patterns")
        rid_to_team, teams_found = discover_teams(metadata)
        unassigned = sum(1 for t in rid_to_team.values() if t == "unassigned")
        console.print(f"  found {len(teams_found)} candidate teams: "
                      f"[bold]{', '.join(teams_found)}[/]   "
                      f"({unassigned} resources unassigned)")
        console.print("[dim]  These are guesses from naming patterns — confirm a few "
                      "via `costdna learn` to bootstrap real attribution.[/]")
        # Stash so the operator can save it.
        if save_dir:
            save_dir.mkdir(parents=True, exist_ok=True)
            pd.DataFrame([{"resource_id": rid, "team_guess": t}
                          for rid, t in rid_to_team.items()]).to_csv(
                save_dir / "discovered.csv", index=False)
            console.print(f"  wrote guesses to [bold]{save_dir / 'discovered.csv'}[/]")
        return

    data = to_pyg(graph, labels)
    console.print(f"[bold cyan]→[/] Training GraphSAGE ({len(active_teams)} classes)")
    result = train_model(data, n_classes=len(active_teams), epochs=epochs, seed=seed)

    def _idx(p: int) -> str:
        return active_teams[p] if 0 <= p < len(active_teams) else "unknown"

    pred_df = pd.DataFrame({
        "resource_id": data.node_ids,
        "team_pred": [_idx(int(p)) for p in result.predictions],
        "confidence": result.confidences,
    }).merge(
        metadata[["resource_id", "resource_type"]
                 + (["team"] if "team" in metadata.columns else [])
                 + (["kind"] if "kind" in metadata.columns else [])],
        on="resource_id", how="left",
    )
    if "team" in pred_df.columns:
        pred_df = pred_df.rename(columns={"team": "team_truth"})

    # Per-resource "why" — naming-signal hints for each prediction. Operator-readable.
    from costdna.semantic import extract_signal_explanations
    pred_team_names = [_idx(int(p)) for p in result.predictions]
    # Defensive: dedupe in case metadata has duplicate resource_ids (rare,
    # but synthetic-generator collisions or merge artifacts can cause it).
    md_unique = metadata.drop_duplicates(subset=["resource_id"], keep="first")
    md_aligned = (md_unique.set_index("resource_id")
                            .reindex(data.node_ids)
                            .reset_index())
    expl_df = extract_signal_explanations(md_aligned, pred_team_names)
    pred_df = pred_df.merge(expl_df, on="resource_id", how="left")

    # Headline output first — what a non-ML user actually wants.
    summary = build_summary(pred_team_names, result.confidences,
                            data.node_ids, signals, metadata)
    render_executive_summary(summary, console=console)

    render_metrics(result.train_acc, result.test_acc,
                   baseline=1.0 / len(active_teams), console=console)
    render_attribution(pred_df,
                       show_truth=show_truth and "team_truth" in pred_df.columns,
                       show_kind=show_kind and "kind" in pred_df.columns,
                       console=console)

    attribution = attributed_dollars(signals, metadata, result.predictions,
                                     data.node_ids, active_teams)
    render_dollars(attribution, console=console)

    # Anomalies — resources that don't fit any team's centroid.
    train_mask_arr = np.zeros(data.y.size(0), dtype=bool)
    train_mask_arr[data.labeled_mask.cpu().numpy()] = True
    anomalies = find_anomalies(
        embeddings=result.embeddings,
        predictions=result.predictions,
        confidences=result.confidences,
        node_ids=data.node_ids,
        train_labels=data.y.cpu().numpy(),
        train_mask=train_mask_arr,
        teams=active_teams,
        graph=graph,
    )
    if anomalies:
        console.print()
        render_anomalies(anomalies, console=console)

    console.print("[bold cyan]→[/] Looking for cost spikes")
    explanations = explain_top_spikes(signals, deploys, active_teams, top_n=5)
    render_explanations(explanations, console=console)

    if save_dir:
        save_dir.mkdir(parents=True, exist_ok=True)
        signals.to_csv(save_dir / "signals.csv", index=False)
        metadata.to_csv(save_dir / "metadata.csv", index=False)
        flows.to_csv(save_dir / "flows.csv", index=False)
        deploys.to_csv(save_dir / "deploys.csv", index=False)
        pred_df.to_csv(save_dir / "predictions.csv", index=False)
        np.save(save_dir / "embeddings.npy", result.embeddings)

        if save_umap:
            from costdna.visualize import render_anomaly_scatter, render_umap
            console.print("[bold cyan]→[/] Rendering UMAP plots")
            # Use ground truth if available, otherwise predictions.
            team_for_color = (pred_df["team_truth"]
                              if "team_truth" in pred_df.columns
                              else pred_df["team_pred"]).fillna("unknown").tolist()
            render_umap(result.embeddings, team_for_color,
                        save_dir / "embedding_umap.png",
                        title="GraphSAGE embedding — colored by team")
            render_anomaly_scatter(result.embeddings, team_for_color,
                                   result.confidences,
                                   save_dir / "embedding_umap_anomalies.png")
        with open(save_dir / "explanations.json", "w") as f:
            json.dump([{"resource_id": e.resource_id,
                        "spike_amount": e.spike_amount,
                        "spike_time": e.spike_time.isoformat(),
                        "likely_team": e.likely_team,
                        "p_value": e.p_value, "sentence": e.sentence}
                       for e in explanations], f, indent=2)
        console.print(f"  wrote outputs to [bold]{save_dir}[/]")


@main.command()
@click.option("--synthetic/--live", default=True)
@click.option("--aws-profile", default=None)
@click.option("--region", default="us-east-1")
@click.option("--days", default=14)
@click.option("--seed", default=42)
@click.option("--epochs", default=200)
@click.option("--seeds", default=1, show_default=True,
              help="Number of seeds to average over. >1 reports mean ± std.")
@click.option("--kfold", default=0, show_default=True,
              help="K-fold cross-validation. >0 overrides --seeds.")
@click.option("--labels", "labels_path",
              type=click.Path(exists=True, dir_okay=False, path_type=Path),
              default=None, help="External labels CSV (resource_id,team).")
@click.option("--from-dir", "from_dir",
              type=click.Path(exists=True, file_okay=False, path_type=Path),
              default=None,
              help="Load signals/metadata/flows from a previous --save-dir output "
                   "instead of re-fetching from AWS (avoids CloudTrail throttling).")
@click.option("--azure-trace", "azure_trace",
              type=click.Path(exists=True, dir_okay=False, path_type=Path),
              default=None,
              help="Path to Microsoft Azure Public Dataset vmtable.csv(.gz).")
@click.option("--azure-top-n", default=25, show_default=True)
@click.option("--azure-max-per-sub", default=200, show_default=True)
@click.option("--azure-readings", "azure_readings",
              type=click.Path(exists=True, dir_okay=False, path_type=Path),
              default=None, help="Optional vm_cpu_readings file.")
def benchmark(synthetic, aws_profile, region, days, seed, epochs, seeds, kfold,
              labels_path, from_dir, azure_trace, azure_top_n, azure_max_per_sub, azure_readings):
    """All baselines vs the GNN — multi-seed (--seeds N) or k-fold (--kfold K)."""
    if kfold > 0:
        if from_dir is not None:
            console.print(f"[bold cyan]→[/] Loading from [bold]{from_dir}[/]")
            signals = pd.read_csv(from_dir / "signals.csv", parse_dates=["timestamp"])
            metadata = pd.read_csv(from_dir / "metadata.csv")
            flows_path = from_dir / "flows.csv"
            try:
                flows = (pd.read_csv(flows_path) if flows_path.exists()
                         else pd.DataFrame())
            except pd.errors.EmptyDataError:
                flows = pd.DataFrame()
        else:
            if azure_trace is not None:
                synth = False
            else:
                live = aws_profile is not None
                synth = not live if synthetic is True else (synthetic and not live)
            signals, metadata, flows, _ = _load(
                synth, aws_profile, region, days, seed,
                azure_trace=azure_trace,
                azure_top_n=azure_top_n, azure_max_per_sub=azure_max_per_sub,
                azure_readings=azure_readings
            )
        if labels_path is not None:
            ext = pd.read_csv(labels_path)
            if "team" in metadata.columns:
                metadata = metadata.drop(columns=["team"])
            metadata = metadata.merge(ext[["resource_id", "team"]],
                                      on="resource_id", how="left")
            console.print(f"  merged {metadata['team'].notna().sum()} labels")
        if "team" not in metadata.columns:
            console.print("[red]No labels in metadata.[/]"); sys.exit(1)
        active_teams = _effective_teams(metadata)
        if active_teams != TEAMS:
            console.print(f"  using {len(active_teams)} teams from data")
        _, fnorm, graph, lbls = _prepare_with_teams(signals, metadata, flows, active_teams)
        d = to_pyg(graph, lbls)
        kind_lookup = (dict(zip(metadata["resource_id"], metadata["kind"]))
                       if "kind" in metadata.columns else {})
        ks = [kind_lookup.get(rid, "clean") for rid in d.node_ids]

        console.print(f"[bold cyan]→[/] {kfold}-fold cross-validation "
                      f"({len(active_teams)} classes)")
        agg_rows = run_benchmark_kfold(d, graph, fnorm.values, ks,
                                       k=kfold, seed=seed, epochs=epochs,
                                       n_classes=len(active_teams))
        kinds_seen = sorted({k for r in agg_rows for k in r.per_kind_mean})
        render_multiseed_benchmark(agg_rows, kinds_seen, console=console)
        gnn = agg_rows[-1]
        best = max(r.test_acc_mean for r in agg_rows[:-1])
        console.print(
            f"\n[bold]GNN:[/] [green]{gnn.test_acc_mean:.1%} ±{gnn.test_acc_std:.1%}[/]   "
            f"[bold]Best baseline:[/] {best:.1%}   "
            f"[bold]Lift:[/] [green]{gnn.test_acc_mean - best:+.1%}[/]"
        )
        return

    if seeds > 1:
        seed_list = [seed + i for i in range(seeds)]
        console.print(f"[bold cyan]→[/] Multi-seed benchmark across "
                      f"{seeds} seeds: {seed_list}")

        def build(s):
            sig, md, fl, _ = _load(synthetic, aws_profile, region, days, s)
            _, fnorm, g, lbls = _prepare(sig, md, fl)
            d = to_pyg(g, lbls)
            kind_lookup = (dict(zip(md["resource_id"], md["kind"]))
                           if "kind" in md.columns else {})
            ks = [kind_lookup.get(rid, "clean") for rid in d.node_ids]
            return d, g, fnorm.values, ks

        agg_rows = run_benchmark_multiseed(build, seed_list, epochs=epochs)
        kinds_seen = sorted({k for r in agg_rows for k in r.per_kind_mean})
        render_multiseed_benchmark(agg_rows, kinds_seen, console=console)
        gnn = agg_rows[-1]
        best = max(r.test_acc_mean for r in agg_rows[:-1])
        console.print(
            f"\n[bold]GNN:[/] [green]{gnn.test_acc_mean:.1%} ±{gnn.test_acc_std:.1%}[/]   "
            f"[bold]Best baseline:[/] {best:.1%}   "
            f"[bold]Lift:[/] [green]{gnn.test_acc_mean - best:+.1%}[/]"
        )
        return

    # Single-seed path (kept for fast demos).
    signals, metadata, flows, _ = _load(synthetic, aws_profile, region, days, seed)
    if "team" not in metadata.columns:
        console.print("[red]No labels in metadata — benchmark needs ground truth.[/]")
        sys.exit(1)
    features, features_norm, graph, labels = _prepare(signals, metadata, flows)
    data = to_pyg(graph, labels)

    kinds = []
    kind_lookup = (dict(zip(metadata["resource_id"], metadata["kind"]))
                   if "kind" in metadata.columns else {})
    for rid in data.node_ids:
        kinds.append(kind_lookup.get(rid, "clean"))

    console.print("[bold cyan]→[/] Running benchmark (single seed; pass "
                  "--seeds 5 for variance estimates)")
    rows, gnn = run_benchmark(
        data, graph, features_norm.values, kinds,
        n_classes=len(TEAMS), seed=seed, epochs=epochs,
    )
    kinds_seen = sorted({k for r in rows for k in r.per_kind.keys()})
    render_benchmark(rows, kinds_seen, console=console)
    render_confusion(rows[-1].confusion, TEAMS, console=console)
    best_baseline = max(r.test_acc for r in rows[:-1])
    console.print(f"\n[bold]GNN test acc:[/] [green]{rows[-1].test_acc:.1%}[/]   "
                  f"[bold]Best non-GNN baseline:[/] {best_baseline:.1%}   "
                  f"[bold]Lift:[/] [green]{(rows[-1].test_acc - best_baseline):+.1%}[/]")


@main.command()
@click.option("--synthetic/--live", default=True)
@click.option("--days", default=14)
@click.option("--seed", default=42)
@click.option("--epochs", default=200)
@click.option("--n-seeds", default=5, show_default=True,
              help="Average each ablation across N seeds for stability.")
def ablate(synthetic, days, seed, epochs, n_seeds):
    """Drop each feature group / edge type and report the accuracy delta.

    The component with the biggest negative delta is doing the most work.
    Components with no delta are dead weight.
    """
    signals, metadata, flows, _ = _load(synthetic, None, "us-east-1", days, seed)
    if "team" not in metadata.columns:
        console.print("[red]Need ground truth labels.[/]"); sys.exit(1)
    features, features_norm, graph, labels = _prepare(signals, metadata, flows)
    seeds = [seed + i for i in range(n_seeds)]

    console.print(f"[bold cyan]→[/] Feature ablation (n_seeds={n_seeds})")
    full_acc, feat_rows = run_feature_ablation(
        features_norm, graph, labels, epochs=epochs, seeds=seeds,
    )
    render_ablation(full_acc, feat_rows,
                    title="Feature group ablation (drop one group at a time)",
                    console=console)

    console.print(f"\n[bold cyan]→[/] Edge ablation (n_seeds={n_seeds})")
    edge_full_acc, edge_rows = run_edge_ablation(
        features_norm, metadata, flows, signals, labels,
        epochs=epochs, seeds=seeds,
    )
    render_ablation(edge_full_acc, edge_rows,
                    title="Edge type ablation (drop one edge kind at a time)",
                    console=console)


@main.command()
@click.option("--synthetic/--live", default=True)
@click.option("--days", default=14)
@click.option("--seed", default=42)
@click.option("--epochs", default=200)
@click.option("--n-bins", default=10, show_default=True)
def calibrate(synthetic, days, seed, epochs, n_bins):
    """Reliability diagram: when the model says 0.7, is it right 70% of the time?"""
    signals, metadata, flows, _ = _load(synthetic, None, "us-east-1", days, seed)
    if "team" not in metadata.columns:
        console.print("[red]Need ground truth labels.[/]"); sys.exit(1)
    _, features_norm, graph, labels = _prepare(signals, metadata, flows)
    data = to_pyg(graph, labels)

    console.print("[bold cyan]→[/] Training model")
    result = train_model(data, n_classes=len(TEAMS), epochs=epochs, seed=seed,
                         verbose=False)
    y = data.y.cpu().numpy()
    cal = calibration_curve(result.predictions, result.confidences, y,
                            mask=data.labeled_mask.cpu().numpy(), n_bins=n_bins)
    render_calibration(cal, console=console)
    console.print(f"\n  [bold]Overall accuracy:[/] {cal.overall_acc:.1%}   "
                  f"[bold]Mean confidence:[/] {cal.overall_conf:.1%}   "
                  f"[bold]ECE:[/] {cal.ece:.3f}")


@main.command()
@click.option("--synthetic/--live", default=True)
@click.option("--days", default=14)
@click.option("--seed", default=42)
@click.option("--budget", default=30, show_default=True,
              help="Max number of confirmed labels the operator provides.")
@click.option("--initial", default=4, show_default=True,
              help="Number of seed labels to start with.")
@click.option("--batch", default=2, show_default=True,
              help="How many resources to label per round.")
@click.option("--strategy",
              type=click.Choice(["random", "least_confidence", "margin"]),
              default="least_confidence", show_default=True)
@click.option("--compare-all", is_flag=True,
              help="Run all three strategies side-by-side.")
@click.option("--azure-trace", "azure_trace",
              type=click.Path(exists=True, dir_okay=False, path_type=Path),
              default=None)
@click.option("--azure-top-n", default=10, show_default=True)
@click.option("--azure-max-per-sub", default=200, show_default=True)
def learn(synthetic, days, seed, budget, initial, batch, strategy, compare_all,
          azure_trace, azure_top_n, azure_max_per_sub, azure_readings):
    """Active learning: how many confirmed labels to attribute thousands?"""
    if azure_trace is not None:
        synthetic = False
    signals, metadata, flows, _ = _load(
        synthetic, None, "us-east-1", days, seed,
        azure_trace=azure_trace,
        azure_top_n=azure_top_n, azure_max_per_sub=azure_max_per_sub,
        azure_readings=azure_readings
    )
    if "team" not in metadata.columns:
        console.print("[red]Active learning sim needs ground truth.[/]")
        sys.exit(1)
    active_teams = _effective_teams(metadata)
    _, features_norm, graph, labels = _prepare_with_teams(
        signals, metadata, flows, active_teams)
    data = to_pyg(graph, labels)

    strategies = ["random", "least_confidence", "margin"] if compare_all else [strategy]

    for strat in strategies:
        console.print(f"[bold cyan]→[/] Active learning (strategy={strat}, "
                      f"budget={budget}, batch={batch}, "
                      f"{len(active_teams)} classes)")
        result = active_learning_loop(
            data, n_classes=len(active_teams),
            initial_labels=initial, budget=budget, batch_size=batch,
            strategy=strat, seed=seed,
        )
        render_learning_curve(result.history, strat, console=console)

    if compare_all:
        from rich.table import Table
        from rich import box
        tbl = Table(title="Strategy comparison @ budget", box=box.SIMPLE_HEAD)
        tbl.add_column("Strategy"); tbl.add_column("Test acc @ budget", justify="right")
        for strat in strategies:
            r = active_learning_loop(data, n_classes=len(active_teams),
                                     initial_labels=initial, budget=budget,
                                     batch_size=batch, strategy=strat, seed=seed)
            tbl.add_row(strat, f"{r.history[-1].test_acc:.1%}")
        console.print(tbl)


@main.command()
@click.option("--state-dir", default="runs/watch", show_default=True,
              type=click.Path(file_okay=False, path_type=Path),
              help="Directory holding date-stamped scan results across runs.")
@click.option("--aws-profile", default=None)
@click.option("--region", default="us-east-1", show_default=True)
@click.option("--days", default=1, show_default=True,
              help="Lookback window per scan.")
@click.option("--epochs", default=200, show_default=True)
@click.option("--seed", default=42, show_default=True)
@click.option("--labels", "labels_path",
              type=click.Path(exists=True, dir_okay=False, path_type=Path),
              default=None)
@click.option("--slack-webhook", "slack_webhook", default=None,
              help="Slack/Discord webhook URL. If unset, falls back to "
                   "SLACK_WEBHOOK_URL env var.")
@click.option("--min-confidence", default=0.7, show_default=True)
def watch(state_dir, aws_profile, region, days, epochs, seed, labels_path,
          slack_webhook, min_confidence):
    """Run a fresh scan, diff against the previous run, post a digest.

    Designed to be run on a daily/weekly cron. The state directory
    accumulates a date-stamped subdir per scan, used for drift detection.

    Cron example (daily at 6am UTC):
        0 6 * * *  /usr/local/bin/costdna watch --aws-profile prod \\
                                                --slack-webhook $SLACK_WEBHOOK_URL
    """
    from costdna.watcher import build_digest, post_to_slack, write_digest
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    run_dir = state_dir / today
    run_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"[bold cyan]→[/] Watch run: {today} → [bold]{run_dir}[/]")

    # Reuse the scan command's logic via Click context invocation.
    ctx = click.get_current_context()
    ctx.invoke(
        scan,
        aws_profile=aws_profile,
        region=region,
        days=days,
        synthetic=False if aws_profile else True,
        seed=seed,
        epochs=epochs,
        save_dir=run_dir,
        show_truth=False,
        show_kind=False,
        labels_path=labels_path,
        azure_trace=None,
        azure_top_n=25,
        azure_max_per_sub=200,
        save_umap=False,
        azure_readings=None,
    )

    # Save anomalies separately for the digest builder.
    # (scan already wrote predictions.csv etc; anomalies are in the run output
    # but we don't currently dump them as JSON. Skip for now — the digest
    # gracefully handles missing anomalies.json.)

    console.print("[bold cyan]→[/] Building drift digest")
    digest = build_digest(run_dir, state_dir, confidence_threshold=min_confidence)
    digest_path = write_digest(digest, run_dir)
    console.print(f"  digest written to [bold]{digest_path}[/]")

    # Show the markdown.
    from rich.panel import Panel
    from rich import box
    console.print(Panel(digest.to_markdown(),
                        title=f"Drift digest — {today}",
                        box=box.ROUNDED, border_style="cyan"))

    # Post to Slack if configured.
    webhook = slack_webhook or os.environ.get("SLACK_WEBHOOK_URL")
    if webhook:
        console.print("[bold cyan]→[/] Posting digest to webhook")
        if post_to_slack(digest, webhook):
            console.print("  [green]✓ posted[/]")
        else:
            console.print("  [red]✗ webhook post failed (see log)[/]")
    else:
        console.print("[dim]  No --slack-webhook / SLACK_WEBHOOK_URL set; "
                      "skipping post.[/]")


@main.command()
@click.argument("question", nargs=-1, required=True)
@click.option("--from-dir", "from_dir",
              type=click.Path(exists=True, file_okay=False, path_type=Path),
              required=True,
              help="Directory of a previous `costdna scan --save-dir <dir>` run.")
@click.option("--model", default="gpt-4o", show_default=True,
              help="OpenAI model name.")
@click.option("--api-key", "api_key", default=None,
              help="OPENAI_API_KEY (or set as env var).")
@click.option("--show-tool-calls", is_flag=True,
              help="Print each tool the agent called and what it returned.")
def ask(question, from_dir, model, api_key, show_tool_calls):
    """Ask a natural-language question about your AWS cost attribution.

    Example:
        costdna ask "why did our bill spike Tuesday?" --from-dir runs/today
        costdna ask "which resources are unowned?" --from-dir runs/today
        costdna ask "top 5 spenders on team ml" --from-dir runs/today
    """
    from costdna.agent import ask as agent_ask, load_context
    q = " ".join(question)
    console.print(f"[bold cyan]→[/] Loading scan context from [bold]{from_dir}[/]")
    ctx = load_context(from_dir)
    console.print(f"  {len(ctx.predictions)} resources, "
                  f"{len(ctx.teams)} teams, "
                  f"{len(ctx.signals):,} signal rows")
    console.print(f"\n[bold cyan]?[/] [italic]{q}[/]\n")
    try:
        reply = agent_ask(q, ctx, model=model, api_key=api_key)
    except (ImportError, RuntimeError) as e:
        console.print(f"[red]{e}[/]")
        sys.exit(1)

    if show_tool_calls and reply.tool_calls:
        from rich.table import Table
        from rich import box
        tbl = Table(title="Tool calls", box=box.SIMPLE_HEAD)
        tbl.add_column("Tool"); tbl.add_column("Args"); tbl.add_column("Result (preview)")
        for tc in reply.tool_calls:
            preview = json.dumps(tc["result"], default=str)[:120] + "…"
            tbl.add_row(tc["tool"], json.dumps(tc["args"]), preview)
        console.print(tbl)
        console.print()

    from rich.panel import Panel
    from rich import box
    console.print(Panel(reply.answer, title="CostDNA",
                        box=box.ROUNDED, border_style="green"))


@main.command()
@click.option("--from-dir", "from_dir",
              type=click.Path(exists=True, file_okay=False, path_type=Path),
              required=True,
              help="Directory of a previous `costdna scan --save-dir <dir>` run.")
@click.option("--model", default="gpt-4o", show_default=True)
@click.option("--api-key", "api_key", default=None)
def chat(from_dir, model, api_key):
    """Interactive multi-turn chat with the CostDNA agent.

    Same agent and tools as `costdna ask`, but stays in a loop and
    remembers context across questions. Type 'exit' or Ctrl-D to leave.

    Example session:
        > summarize the account
        > what's racking up the most spend on team ml?
        > tell me about i-0c4f3230 specifically
    """
    from costdna.agent import ask as agent_ask, load_context
    console.print(f"[bold cyan]→[/] Loading scan context from [bold]{from_dir}[/]")
    ctx = load_context(from_dir)
    console.print(f"  {len(ctx.predictions)} resources, "
                  f"{len(ctx.teams)} teams loaded\n")
    console.print("[dim]Type your questions. 'exit' or Ctrl-D to leave.[/]\n")

    history: list[dict] | None = None
    turn = 0
    while True:
        try:
            q = click.prompt(f"[{turn}]", prompt_suffix=" ❯ ", default="",
                              show_default=False)
        except (EOFError, click.exceptions.Abort):
            console.print("\n[dim]bye.[/]")
            return
        q = q.strip()
        if not q:
            continue
        if q.lower() in ("exit", "quit", "bye", ":q"):
            console.print("[dim]bye.[/]")
            return

        try:
            reply = agent_ask(q, ctx, model=model, api_key=api_key,
                              history=history)
        except (ImportError, RuntimeError) as e:
            console.print(f"[red]{e}[/]")
            return
        except KeyboardInterrupt:
            console.print("\n[dim]interrupted.[/]")
            continue

        history = reply.history
        from rich.panel import Panel
        from rich import box
        console.print(Panel(reply.answer, title=f"CostDNA · turn {turn}",
                            box=box.ROUNDED, border_style="green"))
        turn += 1


@main.command("self-eval")
@click.argument("baseline_dir", type=click.Path(exists=True, file_okay=False,
                                                path_type=Path))
@click.argument("current_dir", type=click.Path(exists=True, file_okay=False,
                                               path_type=Path))
@click.option("--labels", "labels_path", required=True,
              type=click.Path(exists=True, dir_okay=False, path_type=Path),
              help="Ground-truth labels CSV (resource_id, team).")
@click.option("--markdown/--rich", default=False,
              help="Emit Slack/Discord-flavoured markdown instead of a rich "
                   "console table (the default).")
@click.option("--exit-on-degradation", is_flag=True,
              help="Exit code 1 if the overall accuracy delta is statistically "
                   "significant and negative. Useful for cron / CI.")
def self_eval_cmd(baseline_dir: Path, current_dir: Path,
                  labels_path: Path, markdown: bool,
                  exit_on_degradation: bool) -> None:
    """Compare two scan runs against ground-truth labels; report accuracy drift.

    Closes the loop on production deployments: drift detection
    (`costdna diff`) catches changes in *what* the model predicts;
    self-eval catches changes in *whether the predictions are correct*.

    Expected layout:

    \b
      baseline_dir/predictions.csv   # earlier scan
      current_dir/predictions.csv    # latest scan
      labels.csv                     # ground-truth (resource_id, team)

    The Wilson 95% confidence intervals are sized for the small label
    sets typical in early-stage deployments. A `--exit-on-degradation`
    flag returns non-zero when the overall delta CI excludes zero on
    the wrong side — making this suitable to wire into a daily cron.
    """
    from costdna.self_eval import run_self_eval

    rep = run_self_eval(baseline_dir, current_dir, labels_path)

    if markdown:
        click.echo(rep.as_markdown())
    else:
        marker = "[yellow]⚠[/] " if rep.significant_change else ""
        sign = "+" if rep.overall_delta >= 0 else ""
        console.print()
        console.print(
            f"  {marker}[bold]{rep.baseline_run}[/] → "
            f"[bold]{rep.current_run}[/]   "
            f"({rep.n_labels} labels)"
        )
        console.print(
            f"  Overall: [bold]{rep.baseline_overall.accuracy:.1%}[/]"
            f" → [bold]{rep.current_overall.accuracy:.1%}[/]"
            f"   ({sign}{rep.overall_delta:+.1%})"
        )
        if rep.significant_change:
            console.print(
                "  [yellow]This change is statistically significant "
                "(95% CI of delta excludes 0).[/]"
            )
        console.print()
        from rich.table import Table
        t = Table(show_header=True, header_style="bold")
        t.add_column("Team")
        t.add_column("Baseline", justify="right")
        t.add_column("Current", justify="right")
        t.add_column("Δ", justify="right")
        for cur, base in zip(rep.per_team_current, rep.per_team_baseline):
            delta = cur.accuracy - base.accuracy
            delta_color = (
                "green" if delta > 0.05 else
                "red" if delta < -0.05 else "white"
            )
            t.add_row(
                cur.team,
                f"{base.accuracy:.1%} ({base.n_correct}/{base.n_labeled})",
                f"{cur.accuracy:.1%} ({cur.n_correct}/{cur.n_labeled})",
                f"[{delta_color}]{delta:+.1%}[/]",
            )
        console.print(t)

    if exit_on_degradation and rep.significant_change and rep.overall_delta < 0:
        sys.exit(1)


@main.command()
@click.option("--port", default=8501, show_default=True,
              help="Port for the Streamlit web UI.")
def serve(port: int) -> None:
    """Launch the CostDNA web UI (Streamlit).

    Real users — FinOps engineers, platform leads — don't want a CLI. They
    want to look at predictions, filter, click "approve", and export the
    apply commands. That's what `costdna serve` does.
    """
    try:
        import streamlit  # noqa: F401
    except ImportError:
        console.print("[red]Streamlit isn't installed.[/]")
        console.print("  Install the optional UI dependency:  "
                      "[bold]pip install 'costdna[ui]'[/]")
        sys.exit(1)
    import subprocess
    from pathlib import Path as _P
    webapp = _P(__file__).parent / "webapp.py"
    console.print(f"[bold cyan]→[/] Launching CostDNA web UI on "
                  f"[bold]http://localhost:{port}[/]")
    # Use `sys.executable -m streamlit` so we always run the streamlit that
    # belongs to the same venv as costdna — independent of PATH.
    subprocess.run([
        sys.executable, "-m", "streamlit", "run", str(webapp),
        "--server.port", str(port),
        "--server.headless", "true",
    ])


@main.command()
@click.option("--aws-profile", default=None)
@click.option("--region", default="us-east-1")
@click.option("--days", default=14)
def discover(aws_profile, region, days):
    """Auto-discover teams from IAM role naming patterns. Read-only — no model."""
    if aws_profile:
        sigs, md, fl, _ = collect_aws_signals(profile=aws_profile, region=region, days=days)
    else:
        sigs, md, fl, _ = generate_synthetic_signals(seed=42)
    if md.empty:
        console.print("[red]No resources found.[/]")
        sys.exit(1)
    rid_to_team, teams_found = discover_teams(md)
    counts: dict[str, int] = {}
    for t in rid_to_team.values():
        counts[t] = counts.get(t, 0) + 1
    from rich.table import Table
    from rich import box
    tbl = Table(title=f"Discovered teams from {len(md)} resources",
                box=box.SIMPLE_HEAD)
    tbl.add_column("Team (guess)", style="bold")
    tbl.add_column("Resources", justify="right")
    for t in sorted(counts, key=lambda x: -counts[x]):
        tbl.add_row(t, str(counts[t]))
    console.print(tbl)
    console.print("[dim]Use `costdna learn` to confirm these guesses with a few "
                  "labeled resources, then `costdna scan` for full attribution.[/]")


@main.command()
@click.option("--aws-profile", default=None)
@click.option("--region", default="us-east-1", show_default=True)
def doctor(aws_profile, region):
    """Preflight: catch every reason a real-AWS run will fail before it does."""
    from costdna.doctor import run_doctor
    from rich.table import Table
    from rich import box
    console.print(f"[bold cyan]→[/] Running preflight (profile={aws_profile or 'default'}, "
                  f"region={region})")
    checks = run_doctor(aws_profile, region)

    tbl = Table(box=box.SIMPLE_HEAD)
    tbl.add_column("Check", style="bold")
    tbl.add_column("Status", justify="center")
    tbl.add_column("Detail")
    for c in checks:
        color = {"ok": "green", "warn": "yellow", "fail": "red"}[c.status]
        glyph = {"ok": "✓", "warn": "⚠", "fail": "✗"}[c.status]
        tbl.add_row(c.name, f"[{color}]{glyph} {c.status.upper()}[/]", c.message)
        if c.fix_hint:
            tbl.add_row("", "", f"[dim]→ {c.fix_hint}[/]")
    console.print(tbl)

    failed = [c for c in checks if c.status == "fail"]
    if failed:
        console.print(f"\n[red]{len(failed)} check(s) failed.[/] Fix these before "
                      "running `costdna scan`.")
        sys.exit(1)
    warnings = [c for c in checks if c.status == "warn"]
    if warnings:
        console.print(f"\n[yellow]{len(warnings)} warning(s).[/] Scan will run but "
                      "with reduced signal.")
    else:
        console.print("\n[green]All clear.[/] Run `costdna scan --aws-profile "
                      f"{aws_profile or 'default'}` next.")


@main.command()
@click.option("--predictions", "predictions_path",
              type=click.Path(exists=True, path_type=Path), required=True,
              help="Path to predictions.csv from a prior `costdna scan --save-dir` run.")
@click.option("--min-confidence", default=0.7, show_default=True)
@click.option("--apply", "do_apply", is_flag=True,
              help="Actually call AWS to write tags. Default is dry-run "
                   "(print commands only).")
@click.option("--aws-profile", default=None)
@click.option("--region", default="us-east-1")
def apply(predictions_path, min_confidence, do_apply, aws_profile, region):
    """Write predicted teams back to AWS as tags. Defaults to dry-run."""
    df = pd.read_csv(predictions_path)
    ops = build_tag_ops(df, min_confidence=min_confidence)

    if not ops:
        console.print(f"[yellow]No predictions ≥ {min_confidence:.2f} confidence. "
                      "Nothing to tag.[/]")
        return

    console.print(f"[bold]{len(ops)}[/] resources at ≥{min_confidence:.0%} confidence "
                  "will be tagged:")
    by_team = {}
    for op in ops:
        by_team.setdefault(op.team, []).append(op)
    for team, team_ops in sorted(by_team.items()):
        console.print(f"  [cyan]{team}[/]: {len(team_ops)} resources")

    if not do_apply:
        console.print("\n[bold]Dry run — emitting AWS CLI commands "
                      "(no changes made):[/]\n")
        for op in ops[:50]:
            console.print(f"[dim]# conf={op.confidence:.2f}[/]  {op.cli_command}")
        if len(ops) > 50:
            console.print(f"[dim]... and {len(ops) - 50} more.[/]")
        console.print("\n[bold]Run with --apply to actually write these tags.[/]")
        return

    console.print(f"\n[bold red]LIVE MODE[/] — writing tags to "
                  f"{aws_profile or 'default'} in {region}.")
    if not click.confirm("Proceed?", default=False):
        console.print("Aborted.")
        return
    succeeded, failed = apply_tags_live(ops, profile=aws_profile, region=region)
    console.print(f"\n[green]✓ {succeeded} tagged[/]   "
                  f"[red]✗ {failed} failed[/]")


@main.command()
@click.option("--old", "old_path", type=click.Path(exists=True, path_type=Path), required=True,
              help="Earlier predictions.csv")
@click.option("--new", "new_path", type=click.Path(exists=True, path_type=Path), required=True,
              help="Later predictions.csv")
@click.option("--min-confidence", default=0.7, show_default=True)
def diff(old_path, new_path, min_confidence):
    """Drift detection — show resources whose predicted team changed."""
    from rich.table import Table
    from rich import box
    old = pd.read_csv(old_path)
    new = pd.read_csv(new_path)
    events = compute_drift(old, new, confidence_threshold=min_confidence)

    if not events:
        console.print("[green]No drift detected. Predictions stable across runs.[/]")
        return

    by_severity: dict[str, int] = {}
    for e in events:
        by_severity[e.severity] = by_severity.get(e.severity, 0) + 1
    console.print(f"[bold]{len(events)} resources changed team[/] "
                  f"(major: {by_severity.get('major', 0)}, "
                  f"minor: {by_severity.get('minor', 0)}, "
                  f"low-conf: {by_severity.get('low_confidence', 0)})")

    tbl = Table(title="Drift events", box=box.ROUNDED)
    tbl.add_column("Resource", style="bold")
    tbl.add_column("Old →", justify="right")
    tbl.add_column("New", justify="left")
    tbl.add_column("Conf old/new", justify="right")
    tbl.add_column("Severity", justify="center")
    for e in events[:50]:
        sev_color = {"major": "red", "minor": "yellow",
                     "low_confidence": "dim"}[e.severity]
        tbl.add_row(
            e.resource_id,
            f"[red]{e.old_team}[/]",
            f"[green]{e.new_team}[/]",
            f"{e.old_confidence:.2f} / {e.new_confidence:.2f}",
            f"[{sev_color}]{e.severity}[/]",
        )
    console.print(tbl)
    if len(events) > 50:
        console.print(f"[dim]... and {len(events) - 50} more.[/]")


@main.command()
@click.option("--signals", "signals_path", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--metadata", "meta_path", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--flows", "flows_path", type=click.Path(exists=True, path_type=Path), default=None)
@click.option("--deploys", "deploys_path", type=click.Path(exists=True, path_type=Path), default=None)
def inspect(signals_path, meta_path, flows_path, deploys_path):
    """Re-run the model on a previously saved set of signals."""
    signals = pd.read_csv(signals_path, parse_dates=["timestamp"])
    metadata = pd.read_csv(meta_path)
    flows = pd.read_csv(flows_path) if flows_path else pd.DataFrame()
    if "team" not in metadata.columns:
        console.print("[red]metadata.csv has no 'team' column — cannot train.[/]")
        sys.exit(1)
    _, features_norm, graph, labels = _prepare(signals, metadata, flows)
    data = to_pyg(graph, labels)
    result = train_model(data, n_classes=len(TEAMS), epochs=200)
    render_metrics(result.train_acc, result.test_acc, baseline=1.0/len(TEAMS), console=console)


if __name__ == "__main__":
    main()
