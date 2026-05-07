"""Causal spike explainer.

Given a resource's hourly cost time series and a per-team deploy event series,
ask: do team X's deploys *Granger-cause* this resource's cost spikes?

A deploy at hour h adds 1 to that team's hourly deploy count. The cost series
is bucketed to hours, then we run grangercausalitytests at lags 1..max_lag
and take the smallest p-value.

Output is a human-readable string the demo can show alongside the spike.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass

import pandas as pd

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)


@dataclass
class SpikeExplanation:
    resource_id: str
    spike_amount: float
    spike_time: pd.Timestamp
    likely_team: str
    p_value: float
    nearest_deploy: dict | None  # {team, repo, commit, timestamp}
    sentence: str


def _hourly_cost(signals: pd.DataFrame, resource_id: str) -> pd.Series:
    cost = signals[(signals["resource_id"] == resource_id)
                   & (signals["signal_type"] == "cost")].copy()
    if cost.empty:
        return pd.Series(dtype=float)
    cost = cost.set_index("timestamp").sort_index()
    return cost["value"].astype(float).resample("1h").sum().fillna(0.0)


def _hourly_deploys(deploys: pd.DataFrame, team: str) -> pd.Series:
    if deploys.empty or "team" not in deploys.columns:
        return pd.Series(dtype=float)
    d = deploys[deploys["team"] == team].copy()
    if d.empty:
        return pd.Series(dtype=float)
    d = d.set_index("timestamp").sort_index()
    return d.assign(_one=1.0)["_one"].resample("1h").sum().fillna(0.0)


def _granger_pvalue(cost: pd.Series, deploys: pd.Series, max_lag: int = 6) -> float:
    """Lower p = stronger evidence that deploys precede cost changes."""
    from statsmodels.tsa.stattools import grangercausalitytests

    # Align on a common index.
    df = pd.concat([cost.rename("cost"), deploys.rename("dep")], axis=1).fillna(0.0)
    if len(df) < max_lag * 4 or df["cost"].std() == 0 or df["dep"].std() == 0:
        return 1.0
    try:
        res = grangercausalitytests(df[["cost", "dep"]], maxlag=max_lag, verbose=False)
        return min(r[0]["ssr_ftest"][1] for r in res.values())
    except Exception:
        return 1.0


def _detect_spikes(cost: pd.Series, k: float = 3.0) -> list[tuple[pd.Timestamp, float]]:
    """Return (timestamp, amount) pairs where hourly cost is >k std above the mean."""
    if cost.empty:
        return []
    mu, sigma = cost.mean(), cost.std()
    if sigma == 0:
        return []
    spikes = cost[cost > mu + k * sigma]
    return list(zip(spikes.index, spikes.values))


def explain_resource(
    resource_id: str,
    signals: pd.DataFrame,
    deploys: pd.DataFrame,
    teams: tuple[str, ...],
) -> SpikeExplanation | None:
    cost = _hourly_cost(signals, resource_id)
    spikes = _detect_spikes(cost)
    if not spikes:
        return None
    spike_time, spike_amount = max(spikes, key=lambda s: s[1])

    best_team, best_p = None, 1.0
    for team in teams:
        dep = _hourly_deploys(deploys, team)
        p = _granger_pvalue(cost, dep)
        if p < best_p:
            best_team, best_p = team, p

    nearest = None
    if best_team is not None and not deploys.empty:
        cand = deploys[(deploys["team"] == best_team)
                       & (deploys["timestamp"] <= spike_time)].copy()
        if not cand.empty:
            cand["lag_h"] = (spike_time - cand["timestamp"]).dt.total_seconds() / 3600
            cand = cand[(cand["lag_h"] > 0) & (cand["lag_h"] <= 6)]
            if not cand.empty:
                nearest = cand.sort_values("lag_h").iloc[0].to_dict()

    if best_team and best_p < 0.05 and nearest:
        ts = pd.Timestamp(nearest["timestamp"]).strftime("%a %H:%M")
        sentence = (
            f"Resource {resource_id} had a ${spike_amount:.2f} cost spike at "
            f"{spike_time.strftime('%a %H:%M')}. Team {best_team}'s deploy at "
            f"{ts} (commit {nearest['commit']}, repo {nearest['repo']}) is the "
            f"most likely cause (p={best_p:.3f})."
        )
    elif best_team:
        sentence = (
            f"Resource {resource_id} had a ${spike_amount:.2f} cost spike at "
            f"{spike_time.strftime('%a %H:%M')}. Closest causal signal is team "
            f"{best_team} (p={best_p:.3f}), but no nearby deploy was found."
        )
    else:
        sentence = (
            f"Resource {resource_id} had a ${spike_amount:.2f} cost spike at "
            f"{spike_time.strftime('%a %H:%M')}, but no team's deploy pattern "
            f"shows a causal link."
        )

    return SpikeExplanation(
        resource_id=resource_id,
        spike_amount=float(spike_amount),
        spike_time=spike_time,
        likely_team=best_team or "unknown",
        p_value=float(best_p),
        nearest_deploy=nearest,
        sentence=sentence,
    )


def explain_top_spikes(
    signals: pd.DataFrame,
    deploys: pd.DataFrame,
    teams: tuple[str, ...],
    top_n: int = 5,
) -> list[SpikeExplanation]:
    """Find the N largest cost spikes across all resources and explain them."""
    if signals.empty:
        return []
    candidates = []
    for rid in signals["resource_id"].unique():
        ex = explain_resource(rid, signals, deploys, teams)
        if ex:
            candidates.append(ex)
    candidates.sort(key=lambda e: e.spike_amount, reverse=True)
    return candidates[:top_n]
