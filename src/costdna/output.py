"""Rich-formatted output for the CLI."""

from __future__ import annotations

import numpy as np
import pandas as pd  # noqa: F401  # used in type hints for callers
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table


_TEAM_COLOR = {"backend": "cyan", "data": "magenta", "ml": "yellow", "platform": "green"}
_KIND_LABEL = {
    "clean": "[dim]clean[/]",
    "shared_service": "[red]shared-svc[/]",
    "reassigned": "[red]reassigned[/]",
    "sparse": "[yellow]sparse[/]",
    "cross_team": "[yellow]cross-team[/]",
}


def _team_color(team: str) -> str:
    return _TEAM_COLOR.get(team, "white")


def render_executive_summary(summary, *, console: Console | None = None) -> None:
    """The headline output. Dollars + action, in a single panel."""
    console = console or Console()
    high_pct = (summary.high_conf_spend / summary.total_spend * 100
                if summary.total_spend else 0)
    review_pct = (summary.review_spend / summary.total_spend * 100
                  if summary.total_spend else 0)

    body_lines = [
        f"[bold]You have ${summary.total_spend:,.2f}[/] in untagged spend "
        f"across [bold]{summary.total_resources}[/] resources.",
        "",
        f"[bold green]✓ Ready to tag:[/] {summary.high_conf_resources} resources, "
        f"${summary.high_conf_spend:,.2f} ({high_pct:.0f}%) at ≥70% confidence",
        f"[bold yellow]⚠ Need review:[/] {summary.review_resources} resources, "
        f"${summary.review_spend:,.2f} ({review_pct:.0f}%) below 70% confidence",
        "",
        "[bold]Recommended actions:[/]",
    ]
    for line in summary.actionable_lines:
        body_lines.append(f"  • {line}")
    body_lines.append("")
    body_lines.append("[dim]  Run `costdna apply --dry-run` to preview tag commands, "
                      "or `costdna apply` to write them.[/]")

    console.print(Panel("\n".join(body_lines),
                        title="CostDNA — Executive summary",
                        box=box.HEAVY, border_style="bright_green"))


def render_attribution(
    df: pd.DataFrame,
    *,
    title: str = "CostDNA — Inferred ownership",
    show_truth: bool = False,
    show_kind: bool = False,
    console: Console | None = None,
) -> None:
    console = console or Console()
    table = Table(title=title, box=box.ROUNDED)
    table.add_column("Resource", style="bold")
    table.add_column("Type", justify="center")
    if show_kind and "kind" in df.columns:
        table.add_column("Kind", justify="left")
    table.add_column("Predicted", justify="left")
    table.add_column("Conf", justify="right")
    if show_truth and "team_truth" in df.columns:
        table.add_column("Truth", justify="left")
        table.add_column("✓", justify="center")

    for _, row in df.iterrows():
        team = str(row["team_pred"])
        conf = float(row["confidence"])
        conf_str = f"[green]{conf:.2f}[/]" if conf > 0.7 else (
            f"[yellow]{conf:.2f}[/]" if conf > 0.5 else f"[red]{conf:.2f}[/]")
        cells = [str(row["resource_id"]), str(row.get("resource_type", ""))]
        if show_kind and "kind" in df.columns:
            cells.append(_KIND_LABEL.get(str(row["kind"]), str(row["kind"])))
        cells.append(f"[{_team_color(team)}]{team}[/]")
        cells.append(conf_str)
        if show_truth and "team_truth" in df.columns:
            truth = str(row["team_truth"])
            cells.append(f"[{_team_color(truth)}]{truth}[/]")
            cells.append("[green]✓[/]" if truth == team else "[red]✗[/]")
        table.add_row(*cells)
    console.print(table)


def render_explanations(explanations: list, *, console: Console | None = None) -> None:
    console = console or Console()
    if not explanations:
        console.print("[dim]No significant cost spikes detected.[/]")
        return
    body = "\n\n".join(f"[bold]•[/] {e.sentence}" for e in explanations)
    console.print(Panel(body, title="Causal spike explanations",
                        box=box.ROUNDED, border_style="bright_blue"))


def render_metrics(train_acc: float, test_acc: float, baseline: float,
                   *, console: Console | None = None) -> None:
    console = console or Console()
    delta = test_acc - baseline
    body = (
        f"[bold]Train accuracy[/]    {train_acc:.1%}\n"
        f"[bold]Test  accuracy[/]    [green]{test_acc:.1%}[/]\n"
        f"[bold]Random baseline[/]   {baseline:.1%}\n"
        f"[bold]Lift over random[/]  [green]+{delta:.1%}[/]"
    )
    console.print(Panel(body, title="Model accuracy",
                        box=box.ROUNDED, border_style="green"))


def render_confusion(cm: np.ndarray, classes: tuple[str, ...],
                     *, console: Console | None = None) -> None:
    console = console or Console()
    table = Table(title="Confusion matrix (rows=truth, cols=pred)", box=box.SIMPLE_HEAD)
    table.add_column("", style="bold")
    for c in classes:
        table.add_column(c, justify="right")
    for i, true_class in enumerate(classes):
        row = [f"[{_team_color(true_class)}]{true_class}[/]"]
        row_total = cm[i].sum() if i < cm.shape[0] else 0
        for j in range(len(classes)):
            v = int(cm[i, j]) if i < cm.shape[0] and j < cm.shape[1] else 0
            if i == j and v > 0:
                row.append(f"[green]{v}[/]")
            elif v > 0:
                row.append(f"[red]{v}[/]")
            else:
                row.append("[dim]·[/]")
        if row_total > 0:
            recall = cm[i, i] / row_total if i < cm.shape[0] else 0
            row[0] += f"  [dim](recall {recall:.0%})[/]"
        table.add_row(*row)
    console.print(table)


def render_benchmark(rows: list, kinds_seen: list[str],
                     *, console: Console | None = None) -> None:
    """Side-by-side comparison: every model × overall test acc × per-kind acc.
    This is the actual research artifact."""
    console = console or Console()

    table = Table(title="Model comparison — accuracy by resource kind",
                  box=box.ROUNDED, show_lines=False)
    table.add_column("Model", style="bold")
    table.add_column("Overall", justify="right")
    for kind in sorted(kinds_seen):
        table.add_column(kind, justify="right")

    # Identify the best per column for highlighting.
    best_overall = max(r.test_acc for r in rows)
    best_per_kind = {kind: max(r.per_kind.get(kind, 0) for r in rows)
                     for kind in kinds_seen}

    for r in rows:
        overall = r.test_acc
        cells = [r.name]
        cells.append(f"[bold green]{overall:.1%}[/]" if abs(overall - best_overall) < 1e-9
                     else f"{overall:.1%}")
        for kind in sorted(kinds_seen):
            acc = r.per_kind.get(kind)
            if acc is None:
                cells.append("[dim]—[/]")
            elif abs(acc - best_per_kind[kind]) < 1e-9:
                cells.append(f"[bold green]{acc:.1%}[/]")
            else:
                cells.append(f"{acc:.1%}")
        table.add_row(*cells)

    console.print(table)


def render_dollars(attribution: dict, total_cost: float | None = None,
                   *, console: Console | None = None) -> None:
    """The headline metric: $ attributed per team."""
    console = console or Console()
    by_team = attribution["by_team"]
    n_per_team = attribution["resources_per_team"]
    total = attribution["total"]

    table = Table(box=box.SIMPLE_HEAD)
    table.add_column("Team", style="bold")
    table.add_column("Resources", justify="right")
    table.add_column("Spend ($)", justify="right")
    table.add_column("Share", justify="right")

    for team in sorted(by_team, key=lambda t: -by_team[t]):
        share = (by_team[team] / total * 100) if total else 0
        table.add_row(
            f"[{_team_color(team)}]{team}[/]",
            str(n_per_team[team]),
            f"${by_team[team]:,.2f}",
            f"{share:.1f}%",
        )
    table.add_row("[bold]TOTAL[/]", str(sum(n_per_team.values())),
                  f"[bold]${total:,.2f}[/]", "100.0%")

    console.print(Panel(table, title="Dollars attributed",
                        box=box.ROUNDED, border_style="bright_green"))


def render_multiseed_benchmark(rows: list, kinds_seen: list[str],
                               *, console: Console | None = None) -> None:
    """Render aggregated mean ± std across seeds. The actually-defensible table."""
    console = console or Console()
    n_seeds = rows[0].n_seeds if rows else 0
    table = Table(
        title=f"Model comparison — accuracy ± 1σ across {n_seeds} seeds",
        box=box.ROUNDED,
    )
    table.add_column("Model", style="bold")
    table.add_column("Overall", justify="right")
    for kind in sorted(kinds_seen):
        table.add_column(kind, justify="right")

    best_overall = max(r.test_acc_mean for r in rows)
    best_per_kind = {kind: max(r.per_kind_mean.get(kind, 0) for r in rows)
                     for kind in kinds_seen}

    for r in rows:
        overall_str = f"{r.test_acc_mean:.1%} ±{r.test_acc_std:.1%}"
        if abs(r.test_acc_mean - best_overall) < 1e-9:
            overall_str = f"[bold green]{overall_str}[/]"
        cells = [r.name, overall_str]
        for kind in sorted(kinds_seen):
            mean = r.per_kind_mean.get(kind)
            std = r.per_kind_std.get(kind, 0.0)
            if mean is None:
                cells.append("[dim]—[/]")
                continue
            s = f"{mean:.0%} ±{std:.0%}"
            if abs(mean - best_per_kind[kind]) < 1e-9:
                cells.append(f"[bold green]{s}[/]")
            else:
                cells.append(s)
        table.add_row(*cells)
    console.print(table)


def render_ablation(full_acc: float, rows: list, title: str,
                    *, console: Console | None = None) -> None:
    """Show feature/edge ablation: how much accuracy drops without each component."""
    console = console or Console()
    table = Table(title=title, box=box.ROUNDED)
    table.add_column("Component dropped", style="bold")
    table.add_column("Test acc", justify="right")
    table.add_column("Δ", justify="right")

    table.add_row("[dim](full model)[/]", f"{full_acc:.1%}", "[dim]—[/]")
    for r in sorted(rows, key=lambda x: x.delta if not np.isnan(x.delta) else 0):
        if np.isnan(r.test_acc):
            table.add_row(r.component, "[dim]n/a[/]", "[dim](no edges)[/]")
            continue
        delta_pct = r.delta
        if delta_pct < -0.02:
            color = "red"
        elif delta_pct < -0.005:
            color = "yellow"
        else:
            color = "dim"
        table.add_row(r.component, f"{r.test_acc:.1%}",
                      f"[{color}]{delta_pct:+.1%}[/]")
    console.print(table)
    console.print("[dim]  Bigger negative Δ = component was carrying more "
                  "of the signal.[/]")


def render_calibration(result, *, console: Console | None = None) -> None:
    """Reliability diagram as ASCII bars. Confidence vs. empirical accuracy."""
    console = console or Console()
    table = Table(
        title=f"Confidence calibration — ECE = {result.ece:.3f} "
              f"(0 = perfectly calibrated)",
        box=box.SIMPLE_HEAD,
    )
    table.add_column("Bin", style="bold")
    table.add_column("N", justify="right")
    table.add_column("Mean conf", justify="right")
    table.add_column("Empirical acc", justify="right")
    table.add_column("Reliability", justify="left")

    bar_width = 24
    for b in result.bins:
        if b.n == 0:
            table.add_row(f"[{b.low:.1f}, {b.high:.1f})",
                          "[dim]0[/]", "[dim]—[/]", "[dim]—[/]", "")
            continue
        conf_pos = min(int(round(b.mean_confidence * bar_width)), bar_width - 1)
        acc_pos = min(int(round(b.accuracy * bar_width)), bar_width - 1)
        diff_color = "green" if abs(b.accuracy - b.mean_confidence) < 0.05 else "red"

        # Build the bar character-by-character with explicit per-char markup,
        # then concatenate. Avoids nested-tag escaping bugs.
        chars = []
        for i in range(bar_width):
            if i == conf_pos and i == acc_pos:
                chars.append(f"[bold {diff_color}]◉[/]")
            elif i == conf_pos:
                chars.append("[bold]│[/]")
            elif i == acc_pos:
                chars.append(f"[{diff_color}]●[/]")
            else:
                chars.append("[dim]·[/]")
        bar_str = "".join(chars)

        gap = b.accuracy - b.mean_confidence
        gap_str = f"[{diff_color}]{gap:+.0%}[/]"
        table.add_row(
            f"[{b.low:.1f}, {b.high:.1f})",
            str(b.n),
            f"{b.mean_confidence:.2f}",
            f"{b.accuracy:.2f}  ({gap_str})",
            bar_str,
        )
    console.print(table)
    console.print("[dim]  │ = mean predicted confidence in bin, "
                  "● = empirical accuracy. Aligned = well calibrated.[/]")


def render_anomalies(anomalies: list, top_n: int = 10,
                     *, console: Console | None = None) -> None:
    """Top suspicious resources — ones that don't fit any team."""
    console = console or Console()
    if not anomalies:
        console.print("[dim]No anomalies detected. Every resource fits a team.[/]")
        return
    table = Table(
        title=f"Top {min(top_n, len(anomalies))} anomalies (don't fit any team)",
        box=box.ROUNDED, border_style="red",
    )
    table.add_column("Resource", style="bold")
    table.add_column("Best guess", justify="left")
    table.add_column("Confidence", justify="right")
    table.add_column("σ from team", justify="right")
    table.add_column("Reason", justify="left")

    for a in anomalies[:top_n]:
        team_color = _team_color(a.predicted_team)
        conf_color = "red" if a.confidence < 0.5 else (
            "yellow" if a.confidence < 0.7 else "green")
        z_color = "red" if a.z_score > 2 else "yellow"
        table.add_row(
            a.resource_id,
            f"[{team_color}]{a.predicted_team}[/]",
            f"[{conf_color}]{a.confidence:.2f}[/]",
            f"[{z_color}]{a.z_score:+.1f}[/]",
            f"[dim]{a.reason}[/]",
        )
    console.print(table)
    console.print("[dim]  Investigate these. They might be vendor resources, "
                  "compromised infra, or a new team forming.[/]")


def render_learning_curve(history: list, strategy: str,
                          *, console: Console | None = None) -> None:
    """ASCII sparkline + per-checkpoint accuracy."""
    console = console or Console()
    table = Table(title=f"Active learning — strategy: {strategy}",
                  box=box.SIMPLE_HEAD)
    table.add_column("Labels", justify="right")
    table.add_column("Test acc", justify="right")
    table.add_column("Overall", justify="right")
    table.add_column("Curve", justify="left")

    if not history:
        return
    max_acc = max(h.test_acc for h in history) or 1.0
    bar_width = 30

    for h in history:
        bar_len = int(round(h.test_acc / max_acc * bar_width))
        bar = "[green]" + "█" * bar_len + "[/]" + "[dim]" + "░" * (bar_width - bar_len) + "[/]"
        table.add_row(
            str(h.n_labels),
            f"{h.test_acc:.1%}",
            f"{h.overall_acc:.1%}",
            bar,
        )
    console.print(table)
