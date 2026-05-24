"""Generate the two images the distribution push needs.

Produces:
  - docs/images/audit-hero.png
      The 97% → 6.9% before/after bar chart. Goes in:
        * README hero
        * Landing page (if hero image is enabled)
        * Twitter Tweet 1
        * LinkedIn featured post header
        * Blog post header

  - docs/outreach/twitter-thread/audit-pandas.png
      The pandas one-liner rendered as code-on-dark-background with the
      `→ 1.0` output highlighted. Goes in:
        * Twitter Tweet 2
        * LinkedIn featured post (alternative image option)
        * Blog post inline

Both are 1600×900 (Twitter / LinkedIn-card-friendly), 2x DPI, white-or-dark
backgrounds matching the landing page palette.

Reproduce: PYTHONPATH=src python scripts/gen-audit-images.py
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib import rcParams

ROOT = Path(__file__).resolve().parent.parent
IMG_DIR = ROOT / "docs" / "images"
TWITTER_DIR = ROOT / "docs" / "outreach" / "twitter-thread"
IMG_DIR.mkdir(parents=True, exist_ok=True)
TWITTER_DIR.mkdir(parents=True, exist_ok=True)

# Shared typography tuned to read at small Twitter-card sizes.
rcParams["font.family"] = "Helvetica Neue"
rcParams["font.size"] = 14
rcParams["axes.spines.top"] = False
rcParams["axes.spines.right"] = False


def make_audit_hero():
    """The 97% → 6.9% before/after bar chart with annotations."""
    fig, ax = plt.subplots(figsize=(16, 9), dpi=150)
    fig.patch.set_facecolor("#fafafa")
    ax.set_facecolor("#fafafa")

    labels = ["First-cut\n(leak unaccounted)", "Honest\n(post-audit)", "Random\nbaseline"]
    values = [97.0, 6.9, 1.0]
    # First bar = light gray with strike-through; second = solid dark; third = light.
    colors = ["#d4d4d8", "#171717", "#a1a1aa"]
    bars = ax.bar(labels, values, color=colors, width=0.55, edgecolor="none")

    # Numeric labels on top of bars.
    for bar, val in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 2,
            f"{val:.1f}%" if val != 6.9 else "6.9%",
            ha="center", va="bottom",
            fontsize=28, fontweight="bold",
            color=bar.get_facecolor() if val != 97 else "#71717a",
        )

    # Strike-through visual on the 97% bar.
    ax.plot(
        [bars[0].get_x() - 0.05, bars[0].get_x() + bars[0].get_width() + 0.05],
        [50, 50],
        color="#71717a", linewidth=3, linestyle="-",
    )

    # Title block above the chart.
    fig.text(
        0.06, 0.92,
        "A 97% cloud-attribution accuracy result.",
        fontsize=32, fontweight="bold", color="#171717",
    )
    fig.text(
        0.06, 0.86,
        "I audited my own work. It was a tautology.",
        fontsize=20, color="#71717a", style="italic",
    )

    # Caption below the chart.
    fig.text(
        0.06, 0.06,
        "Across all 33,205 deployments in Microsoft's published 2.6M-VM Azure trace, "
        "deployment_id mapped 1:1 to subscription_id — every single deployment belonged to exactly one\n"
        "subscription. The graph edge was a database join, not learning. With the leak removed, "
        "honest GraphSAGE accuracy on 100-class attribution: 6.9% (still 12× random, but a long way from 97%).",
        fontsize=12, color="#52525b",
    )
    fig.text(
        0.06, 0.015,
        "github.com/pauti04/CostDNA",
        fontsize=11, color="#a1a1aa", family="monospace",
    )

    ax.set_ylim(0, 110)
    ax.set_ylabel("Test accuracy on 100-class attribution (%)", fontsize=13, color="#52525b", labelpad=15)
    ax.tick_params(axis="both", colors="#71717a", labelsize=12)
    ax.yaxis.set_major_formatter(plt.matplotlib.ticker.PercentFormatter())

    # Subtle horizontal lines at key thresholds.
    ax.axhline(1, color="#e4e4e7", linestyle=":", linewidth=1)
    ax.axhline(50, color="#e4e4e7", linestyle=":", linewidth=1)

    plt.subplots_adjust(left=0.06, right=0.96, top=0.78, bottom=0.20)
    out = IMG_DIR / "audit-hero.png"
    fig.savefig(out, dpi=150, facecolor="#fafafa", edgecolor="none")
    plt.close(fig)
    print(f"Wrote {out.relative_to(ROOT)}")
    return out


def make_audit_pandas_image():
    """The pandas one-liner as a code-on-dark image with `→ 1.0` highlighted."""
    fig, ax = plt.subplots(figsize=(16, 9), dpi=150)
    fig.patch.set_facecolor("#0a0a0a")
    ax.set_facecolor("#0a0a0a")
    ax.axis("off")

    # The "audit" framing at the top.
    fig.text(
        0.06, 0.86,
        "The pandas one-liner that turned my 97% accuracy into 6.9%",
        fontsize=24, fontweight="bold", color="#fafafa",
    )
    fig.text(
        0.06, 0.795,
        "Run this before reporting any cloud-attribution benchmark.",
        fontsize=14, color="#a1a1aa", style="italic",
    )

    # "Terminal window" header decoration.
    term_x, term_y, term_w, term_h = 0.06, 0.30, 0.88, 0.42
    rect = patches.FancyBboxPatch(
        (term_x, term_y), term_w, term_h,
        boxstyle="round,pad=0.012,rounding_size=0.02",
        transform=fig.transFigure,
        linewidth=1, edgecolor="#27272a", facecolor="#1a1a1a",
    )
    fig.patches.append(rect)

    # Three dots like a macOS window.
    for i, color in enumerate(["#ef4444", "#f59e0b", "#10b981"]):
        circ = patches.Circle((term_x + 0.025 + i * 0.018, term_y + term_h - 0.035),
                              radius=0.008, transform=fig.transFigure,
                              facecolor=color, edgecolor="none")
        fig.patches.append(circ)
    fig.text(
        term_x + term_w / 2, term_y + term_h - 0.035,
        "audit.py — checking deployment_id → subscription_id",
        fontsize=11, color="#71717a", ha="center", va="center", family="monospace",
    )

    # The actual code, line by line, with syntax-ish highlighting.
    code_y = term_y + term_h - 0.10
    line_height = 0.045
    code_x = term_x + 0.035

    lines = [
        ("# Is the deployment_id graph edge deterministic of the target?", "#71717a"),
        ("import pandas as pd", "#fafafa"),
        ("", "#fafafa"),
        (">>> (df.groupby(\"deployment_id\")[\"subscription_id\"]", "#fafafa"),
        ("...        .nunique() == 1).mean()", "#fafafa"),
    ]
    for i, (text, color) in enumerate(lines):
        fig.text(code_x, code_y - i * line_height, text,
                 fontsize=15, color=color, family="monospace")

    # The highlighted result line.
    result_y = code_y - len(lines) * line_height - 0.005
    fig.text(code_x, result_y, "→ 1.0",
             fontsize=24, color="#22d3ee", family="monospace", fontweight="bold")
    fig.text(code_x + 0.10, result_y + 0.005,
             "100% of 33,205 deployments map to one subscription.",
             fontsize=12, color="#a1a1aa", family="monospace")
    fig.text(code_x + 0.10, result_y - 0.025,
             "Your graph edge is a database join, not learning.",
             fontsize=12, color="#a1a1aa", family="monospace")

    # Footer.
    fig.text(
        0.06, 0.10,
        "Two unrelated published Microsoft cloud datasets, same leakage pattern.",
        fontsize=14, color="#fafafa", fontweight="bold",
    )
    fig.text(
        0.06, 0.06,
        "Audit + reusable check + honest baselines: github.com/pauti04/CostDNA",
        fontsize=12, color="#71717a",
    )
    fig.text(
        0.06, 0.025,
        "cost-dna.vercel.app",
        fontsize=11, color="#a1a1aa", family="monospace",
    )

    out = TWITTER_DIR / "audit-pandas.png"
    fig.savefig(out, dpi=150, facecolor="#0a0a0a", edgecolor="none")
    plt.close(fig)
    print(f"Wrote {out.relative_to(ROOT)}")
    return out


def make_audit_checklist_image():
    """Carbon-style image of the reusable find_deterministic_edges function.
    Used for Tweet 6."""
    fig, ax = plt.subplots(figsize=(16, 9), dpi=150)
    fig.patch.set_facecolor("#0a0a0a")
    ax.set_facecolor("#0a0a0a")
    ax.axis("off")

    fig.text(
        0.06, 0.88,
        "The two-line minimum standard for cloud-attribution benchmarks",
        fontsize=22, fontweight="bold", color="#fafafa",
    )
    fig.text(
        0.06, 0.825,
        "Drop in any cloud-attribution project before reporting accuracy.",
        fontsize=13, color="#a1a1aa", style="italic",
    )

    # Terminal window.
    term_x, term_y, term_w, term_h = 0.06, 0.16, 0.88, 0.60
    rect = patches.FancyBboxPatch(
        (term_x, term_y), term_w, term_h,
        boxstyle="round,pad=0.012,rounding_size=0.02",
        transform=fig.transFigure,
        linewidth=1, edgecolor="#27272a", facecolor="#1a1a1a",
    )
    fig.patches.append(rect)
    for i, color in enumerate(["#ef4444", "#f59e0b", "#10b981"]):
        circ = patches.Circle((term_x + 0.025 + i * 0.018, term_y + term_h - 0.030),
                              radius=0.007, transform=fig.transFigure,
                              facecolor=color, edgecolor="none")
        fig.patches.append(circ)
    fig.text(
        term_x + term_w / 2, term_y + term_h - 0.030,
        "audit.py — minimum standard for cloud-attribution",
        fontsize=10, color="#71717a", ha="center", va="center", family="monospace",
    )

    code_y = term_y + term_h - 0.085
    line_height = 0.035
    code_x = term_x + 0.035

    lines = [
        ("def find_deterministic_edges(", "#fafafa"),
        ("        df, target_col, candidate_edge_cols, threshold=0.85", "#fafafa"),
        ("):", "#fafafa"),
        ("    \"\"\"Edge columns that deterministically encode the target = leaks.\"\"\"", "#71717a"),
        ("    out = {}", "#fafafa"),
        ("    for col in candidate_edge_cols:", "#fafafa"),
        ("        det = (df.groupby(col)[target_col].nunique() == 1).mean()", "#fafafa"),
        ("        if det >= threshold:", "#fafafa"),
        ("            out[col] = det", "#fafafa"),
        ("    return out", "#fafafa"),
        ("", "#fafafa"),
        (">>> find_deterministic_edges(", "#22d3ee"),
        ("...     df, \"subscription_id\",", "#22d3ee"),
        ("...     [\"deployment_id\", \"vm_category\", \"machine_type\", \"role\"]", "#22d3ee"),
        ("... )", "#22d3ee"),
        ("{\"deployment_id\": 1.0}  # leak — your graph edge is the answer", "#fbbf24"),
    ]
    for i, (text, color) in enumerate(lines):
        fig.text(code_x, code_y - i * line_height, text,
                 fontsize=13, color=color, family="monospace")

    fig.text(
        0.06, 0.10,
        "One function call. Catches the failure mode that inflates published benchmarks by 60-90 points.",
        fontsize=13, color="#fafafa",
    )
    fig.text(
        0.06, 0.06,
        "Full audit + honest post-leak baselines + node2vec comparison: github.com/pauti04/CostDNA",
        fontsize=11, color="#71717a",
    )

    out = TWITTER_DIR / "audit-checklist.png"
    fig.savefig(out, dpi=150, facecolor="#0a0a0a", edgecolor="none")
    plt.close(fig)
    print(f"Wrote {out.relative_to(ROOT)}")
    return out


if __name__ == "__main__":
    make_audit_hero()
    make_audit_pandas_image()
    make_audit_checklist_image()
    print("\nAll three images generated.")
