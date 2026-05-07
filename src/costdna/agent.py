"""LLM agent — natural-language interface over CostDNA's pipeline.

Reframes CostDNA from "ML attribution tool" to "AI agent that answers
natural-language questions about your cloud bill." Same backend pipeline
(features → graph → GraphSAGE → predictions), but the user interface is:

  $ costdna ask "why did our bill spike Tuesday?"
  > Resource `i-0c4f3230` (predicted team: ml, conf 0.92) had a $7.30 cost
  > spike on Tue 16:00. Team ml's deploy at Tue 14:18 (commit a4f2c91, repo
  > ml-training-pipeline) is the most likely cause (Granger p=0.000).

Architecture: Anthropic-style tool use. The LLM calls one of 5-6 tools
that wrap CostDNA's existing functionality, then synthesizes a natural-
language answer from the structured tool results.

Setup:
  pip install 'costdna[agent]'   (installs anthropic SDK)
  export ANTHROPIC_API_KEY=...   (or pass --api-key)
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pandas as pd

log = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-sonnet-4-5"


# ────────────────────────────────────────────────────────────────────────
# Tools — pure-Python functions the LLM can call.
# Each tool gets a JSON schema so Claude knows how to invoke it.
# ────────────────────────────────────────────────────────────────────────


@dataclass
class CostDnaContext:
    """The state an agent needs to answer cost questions about an account.

    Built from a saved scan dir (`runs/...`) — predictions, signals, deploys,
    explanations. The agent reads from this, doesn't run new scans.
    """
    predictions: pd.DataFrame
    signals: pd.DataFrame
    deploys: pd.DataFrame | None
    metadata: pd.DataFrame
    teams: tuple[str, ...]


def load_context(run_dir: str | Path) -> CostDnaContext:
    """Load all the artifacts of a previous `costdna scan --save-dir <run_dir>`."""
    p = Path(run_dir)
    pred = pd.read_csv(p / "predictions.csv")
    md = pd.read_csv(p / "metadata.csv")
    sig_path = p / "signals.csv"
    sig = (pd.read_csv(sig_path, parse_dates=["timestamp"])
           if sig_path.exists() else pd.DataFrame())
    dep_path = p / "deploys.csv"
    dep = (pd.read_csv(dep_path, parse_dates=["timestamp"])
           if dep_path.exists() and dep_path.stat().st_size > 1
           else None)
    teams = tuple(sorted(pred["team_pred"].dropna().unique()))
    return CostDnaContext(predictions=pred, signals=sig, deploys=dep,
                          metadata=md, teams=teams)


# ── Tool implementations ─────────────────────────────────────────────────


def tool_summarize_account(ctx: CostDnaContext) -> dict:
    """High-level rollup: total resources, by-team spend, by-team confidence."""
    n = len(ctx.predictions)
    by_team = (ctx.predictions.groupby("team_pred")
               .agg(n=("resource_id", "count"),
                    avg_conf=("confidence", "mean"))
               .sort_values("n", ascending=False))

    cost_by_team = {}
    if not ctx.signals.empty and "signal_type" in ctx.signals.columns:
        cost = ctx.signals[ctx.signals["signal_type"] == "cost"]
        if not cost.empty:
            cost_by_rid = cost.groupby("resource_id")["value"].sum().to_dict()
            for _, row in ctx.predictions.iterrows():
                t = row["team_pred"]
                cost_by_team[t] = cost_by_team.get(t, 0.0) + float(
                    cost_by_rid.get(row["resource_id"], 0.0))

    return {
        "total_resources": n,
        "teams_found": list(ctx.teams),
        "by_team": [
            {
                "team": team,
                "resources": int(row["n"]),
                "avg_confidence": float(row["avg_conf"]),
                "total_spend": float(cost_by_team.get(team, 0.0)),
            }
            for team, row in by_team.iterrows()
        ],
    }


def tool_attribute_resource(ctx: CostDnaContext, resource_id: str) -> dict:
    """Look up what team owns a specific resource and why."""
    rows = ctx.predictions[ctx.predictions["resource_id"] == resource_id]
    if rows.empty:
        # Try fuzzy match.
        candidates = ctx.predictions[
            ctx.predictions["resource_id"].str.contains(resource_id, case=False, na=False)
        ]
        if not candidates.empty:
            return {
                "exact_match": False,
                "candidates": candidates.head(5).to_dict("records"),
                "error": f"No exact match for {resource_id!r}; "
                         "showing candidates with that substring.",
            }
        return {"error": f"Resource {resource_id!r} not found in this scan."}
    r = rows.iloc[0]
    return {
        "resource_id": r["resource_id"],
        "predicted_team": str(r.get("team_pred")),
        "confidence": float(r["confidence"]),
        "explanation": str(r.get("explanation", "")),
        "resource_type": str(r.get("resource_type", "unknown")),
        "ground_truth_team": (str(r["team_truth"])
                              if "team_truth" in r and pd.notna(r["team_truth"])
                              else None),
    }


def tool_top_spenders(ctx: CostDnaContext, team: str | None = None,
                      limit: int = 10) -> dict:
    """Top resources by total cost, optionally filtered to one team."""
    if ctx.signals.empty:
        return {"error": "No signal data available in this scan."}
    cost = ctx.signals[ctx.signals["signal_type"] == "cost"]
    if cost.empty:
        return {"error": "No cost data in signals."}
    by_rid = cost.groupby("resource_id")["value"].sum().sort_values(ascending=False)
    df = by_rid.reset_index().rename(columns={"value": "total_cost"})
    df = df.merge(ctx.predictions[["resource_id", "team_pred", "confidence"]],
                  on="resource_id", how="left")
    if team:
        df = df[df["team_pred"] == team]
    return {
        "filter_team": team,
        "top_spenders": df.head(limit).to_dict("records"),
    }


def tool_find_cost_spikes(ctx: CostDnaContext, top_n: int = 5) -> dict:
    """Find the largest hourly cost spikes and attribute them to deploys."""
    if ctx.signals.empty:
        return {"error": "No signal data available."}
    from costdna.explain import explain_top_spikes
    explanations = explain_top_spikes(ctx.signals, ctx.deploys or pd.DataFrame(),
                                       ctx.teams, top_n=top_n)
    return {
        "spikes": [
            {
                "resource_id": e.resource_id,
                "spike_amount_usd": e.spike_amount,
                "spike_time": e.spike_time.isoformat(),
                "likely_team": e.likely_team,
                "p_value": e.p_value,
                "human_summary": e.sentence,
            }
            for e in explanations
        ],
    }


def tool_find_anomalies(ctx: CostDnaContext, limit: int = 10) -> dict:
    """Resources that don't fit any team well — investigate manually."""
    df = ctx.predictions.copy()
    df["anomaly_score"] = 1 - df["confidence"]
    anomalous = df.sort_values("anomaly_score", ascending=False).head(limit)
    return {
        "anomalies": [
            {
                "resource_id": r["resource_id"],
                "predicted_team": str(r.get("team_pred")),
                "confidence": float(r["confidence"]),
                "explanation": str(r.get("explanation", "")),
            }
            for _, r in anomalous.iterrows()
        ],
    }


def tool_search_resources(ctx: CostDnaContext, substring: str,
                           limit: int = 20) -> dict:
    """Find resources whose ID matches a substring."""
    df = ctx.predictions
    matches = df[df["resource_id"].str.contains(substring, case=False, na=False)]
    return {
        "substring": substring,
        "n_matches": len(matches),
        "matches": matches.head(limit).to_dict("records"),
    }


def tool_signal_history(ctx: CostDnaContext, resource_id: str,
                         hours: int = 24) -> dict:
    """Recent activity for one resource — events and cost over time."""
    if ctx.signals.empty:
        return {"error": "No signal data available."}
    sigs = ctx.signals[ctx.signals["resource_id"] == resource_id].copy()
    if sigs.empty:
        return {"resource_id": resource_id, "events": 0, "note": "no signals for this resource"}
    sigs = sigs.sort_values("timestamp")
    if len(sigs) > 0 and "timestamp" in sigs.columns:
        cutoff = sigs["timestamp"].max() - pd.Timedelta(hours=hours)
        sigs = sigs[sigs["timestamp"] >= cutoff]
    by_type = sigs.groupby("signal_type").size().to_dict()
    cost_total = float(sigs[sigs["signal_type"] == "cost"]["value"].sum()) if "signal_type" in sigs.columns else 0.0
    sample = sigs.head(10).to_dict("records")
    return {
        "resource_id": resource_id,
        "window_hours": hours,
        "n_events": int(len(sigs)),
        "events_by_type": by_type,
        "total_cost_in_window": cost_total,
        "first_10_events": sample,
    }


def tool_find_idle(ctx: CostDnaContext, max_events: int = 5) -> dict:
    """Resources with very few events — candidates for cleanup or deprecation."""
    if ctx.signals.empty:
        return {"error": "No signal data available."}
    counts = (ctx.signals.groupby("resource_id").size()
              .reset_index(name="n_events"))
    idle = counts[counts["n_events"] <= max_events]
    idle = idle.merge(ctx.predictions[["resource_id", "team_pred", "confidence",
                                       "resource_type"]],
                       on="resource_id", how="left")
    cost = ctx.signals[ctx.signals["signal_type"] == "cost"]
    if not cost.empty:
        cost_per = cost.groupby("resource_id")["value"].sum().reset_index(name="total_cost")
        idle = idle.merge(cost_per, on="resource_id", how="left")
    idle = idle.sort_values("total_cost" if "total_cost" in idle.columns else "n_events",
                             ascending=False)
    return {
        "max_events_threshold": max_events,
        "n_idle": len(idle),
        "resources": idle.head(20).to_dict("records"),
    }


def tool_compare_teams(ctx: CostDnaContext, team_a: str, team_b: str) -> dict:
    """Side-by-side comparison of two teams: resource counts, spend, top resources."""
    cost_per_rid = {}
    if not ctx.signals.empty:
        c = ctx.signals[ctx.signals["signal_type"] == "cost"]
        if not c.empty:
            cost_per_rid = c.groupby("resource_id")["value"].sum().to_dict()

    def stats(team):
        rows = ctx.predictions[ctx.predictions["team_pred"] == team]
        spend = sum(float(cost_per_rid.get(r, 0.0)) for r in rows["resource_id"])
        types = rows["resource_type"].value_counts().to_dict() if "resource_type" in rows.columns else {}
        rows_with_cost = rows.assign(cost=rows["resource_id"].map(cost_per_rid).fillna(0.0))
        top3 = (rows_with_cost.sort_values("cost", ascending=False)
                              .head(3)[["resource_id", "cost"]]
                              .to_dict("records"))
        return {
            "team": team,
            "n_resources": int(len(rows)),
            "total_spend": spend,
            "avg_confidence": float(rows["confidence"].mean()) if len(rows) else 0.0,
            "by_type": types,
            "top_3_resources": top3,
        }

    return {"team_a": stats(team_a), "team_b": stats(team_b)}


# Tool registry — JSON schemas for Claude.
TOOLS_SPEC = [
    {
        "name": "summarize_account",
        "description": "Get a high-level summary of the AWS account: total "
                       "resources, teams found, per-team resource counts and spend.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "attribute_resource",
        "description": "Look up which team owns a specific AWS resource and "
                       "why. Returns predicted team, confidence, and the "
                       "naming-signal explanation.",
        "input_schema": {
            "type": "object",
            "properties": {
                "resource_id": {
                    "type": "string",
                    "description": "AWS resource ID (e.g. 'i-0c4f3230', "
                                   "'prod-bucket-abc123')",
                },
            },
            "required": ["resource_id"],
        },
    },
    {
        "name": "top_spenders",
        "description": "Return the top resources by total cost in the scan window. "
                       "Optionally filter by a single team.",
        "input_schema": {
            "type": "object",
            "properties": {
                "team": {
                    "type": "string",
                    "description": "Optional: filter to a specific team. "
                                   "If omitted, returns top spenders across all teams.",
                },
                "limit": {"type": "integer", "default": 10},
            },
        },
    },
    {
        "name": "find_cost_spikes",
        "description": "Find the largest cost spikes in the scan window, and "
                       "attribute each to a likely team's deployment via Granger "
                       "causality. Returns spike $ amount, time, likely team, p-value.",
        "input_schema": {
            "type": "object",
            "properties": {
                "top_n": {"type": "integer", "default": 5},
            },
        },
    },
    {
        "name": "find_anomalies",
        "description": "Return resources that don't fit any known team well — "
                       "low confidence and/or far from team centroids in embedding "
                       "space. These are candidates for manual investigation "
                       "(vendor infra, ex-employee leftovers, shadow IT).",
        "input_schema": {
            "type": "object",
            "properties": {"limit": {"type": "integer", "default": 10}},
        },
    },
    {
        "name": "search_resources",
        "description": "Find resources whose ID contains a given substring. "
                       "Useful when the user describes a resource by partial name.",
        "input_schema": {
            "type": "object",
            "properties": {
                "substring": {"type": "string"},
                "limit": {"type": "integer", "default": 20},
            },
            "required": ["substring"],
        },
    },
    {
        "name": "signal_history",
        "description": "Show recent CloudTrail events and cost samples for a "
                       "specific resource over a time window. Useful for "
                       "answering 'what did this resource do recently?'",
        "input_schema": {
            "type": "object",
            "properties": {
                "resource_id": {"type": "string"},
                "hours": {"type": "integer", "default": 24},
            },
            "required": ["resource_id"],
        },
    },
    {
        "name": "find_idle",
        "description": "Resources with very few events in the scan window. "
                       "Candidates for cleanup, deprecation, or cost reduction. "
                       "Returns total cost for each so you can prioritize.",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_events": {
                    "type": "integer", "default": 5,
                    "description": "Threshold for 'idle' — resources with at "
                                   "most this many events are returned.",
                },
            },
        },
    },
    {
        "name": "compare_teams",
        "description": "Side-by-side comparison of two teams: resource counts, "
                       "total spend, average confidence, breakdown by resource "
                       "type, top 3 resources each.",
        "input_schema": {
            "type": "object",
            "properties": {
                "team_a": {"type": "string"},
                "team_b": {"type": "string"},
            },
            "required": ["team_a", "team_b"],
        },
    },
]

TOOL_REGISTRY: dict[str, Callable[..., dict]] = {
    "summarize_account":   tool_summarize_account,
    "attribute_resource":  tool_attribute_resource,
    "top_spenders":        tool_top_spenders,
    "find_cost_spikes":    tool_find_cost_spikes,
    "find_anomalies":      tool_find_anomalies,
    "search_resources":    tool_search_resources,
    "signal_history":      tool_signal_history,
    "find_idle":           tool_find_idle,
    "compare_teams":       tool_compare_teams,
}


# ────────────────────────────────────────────────────────────────────────
# Agent loop
# ────────────────────────────────────────────────────────────────────────


SYSTEM_PROMPT = """\
You are CostDNA, an AI agent that answers natural-language questions about \
AWS cloud cost attribution. You have access to a set of tools that query \
behavioral, semantic, and graph-based attribution data from a previously- \
completed scan of an AWS account.

When a user asks a question:
  1. Decide which tool(s) to call and with what arguments.
  2. Use the structured results to compose a concise, accurate answer in plain \
English.
  3. Always cite specific resource IDs, teams, dollar amounts, timestamps, and \
confidence scores from the tool results.
  4. If a prediction has low confidence, say so. If the data doesn't support \
a confident answer, say that too.
  5. Never invent resource IDs, teams, or numbers. Only use values returned by \
the tools.

Format answers as short paragraphs with bullet points for lists. Prefer \
short answers (2-5 sentences) over long ones. Surface the most impactful \
information first."""


@dataclass
class AgentReply:
    answer: str
    tool_calls: list[dict]   # each: {"tool": name, "args": ..., "result": ...}
    raw_response: dict
    history: list[dict] | None = None   # full message list for multi-turn


def ask(question: str, ctx: CostDnaContext, *, model: str = DEFAULT_MODEL,
        api_key: str | None = None, max_iterations: int = 6,
        history: list[dict] | None = None) -> AgentReply:
    """Send a question to Claude with the CostDNA tools available; loop on
    tool_use until the model produces a final answer.

    `history`: optional prior messages list for multi-turn conversation.
    Append the current question; the function returns a new history list
    including the assistant's reply, ready to feed into the next call.
    """
    try:
        import anthropic
    except ImportError as e:
        raise ImportError(
            "The agent requires anthropic. Install with: pip install 'costdna[agent]'"
        ) from e

    api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY not set. Get one at https://console.anthropic.com/, "
            "then `export ANTHROPIC_API_KEY=...` (or pass --api-key)."
        )

    client = anthropic.Anthropic(api_key=api_key)
    messages: list[dict] = list(history or [])
    messages.append({"role": "user", "content": question})
    tool_calls: list[dict] = []

    for _ in range(max_iterations):
        resp = client.messages.create(
            model=model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOLS_SPEC,
            messages=messages,
        )

        # If the model is done thinking, return the answer.
        if resp.stop_reason in ("end_turn", "stop_sequence"):
            answer = "".join(b.text for b in resp.content if hasattr(b, "text"))
            messages.append({"role": "assistant", "content": resp.content})
            return AgentReply(answer=answer.strip(), tool_calls=tool_calls,
                              raw_response={"id": resp.id, "model": resp.model},
                              history=messages)

        # Otherwise it requested tool use. Execute and append tool_result blocks.
        if resp.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": resp.content})
            tool_results = []
            for block in resp.content:
                if block.type != "tool_use":
                    continue
                tool_name = block.name
                tool_args = dict(block.input)
                fn = TOOL_REGISTRY.get(tool_name)
                if fn is None:
                    result = {"error": f"unknown tool {tool_name!r}"}
                else:
                    try:
                        result = fn(ctx, **tool_args)
                    except Exception as e:
                        result = {"error": f"{type(e).__name__}: {e}"}
                tool_calls.append({"tool": tool_name, "args": tool_args,
                                    "result": result})
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result, default=str),
                })
            messages.append({"role": "user", "content": tool_results})
            continue

        # Unexpected stop reason — bail.
        break

    return AgentReply(
        answer="(agent ran out of iterations without producing a final answer)",
        tool_calls=tool_calls,
        raw_response={},
    )
