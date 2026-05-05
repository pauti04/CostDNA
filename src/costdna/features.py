"""Per-resource feature extraction.

The build guide specifies six baseline features that capture team-distinguishing
behavior:

  1. event_count       — total CloudTrail events in window
  2. unique_users      — distinct IAM principals
  3. peak_hour         — modal hour-of-day for activity (0-23)
  4. weekend_ratio     — fraction of events on Sat/Sun
  5. unique_roles      — distinct IAM roles touching the resource
  6. cross_account     — 1 if ever accessed from a different AWS account, else 0

Plus three from Week 5 cost time-series features:

  7. cost_slope        — linear regression slope of hourly cost over the window
  8. cost_variance     — variance of hourly cost
  9. cost_autocorr     — lag-24 autocorrelation (catches daily periodicity)
"""

from __future__ import annotations

import numpy as np
import pandas as pd

FEATURE_COLUMNS = (
    "event_count",
    "unique_users",
    "peak_hour",
    "weekend_ratio",
    "unique_roles",
    "cross_account",
    "cost_slope",
    "cost_variance",
    "cost_autocorr",
)


def _autocorr(x: np.ndarray, lag: int) -> float:
    if len(x) <= lag or x.std() == 0:
        return 0.0
    a = x[:-lag] - x[:-lag].mean()
    b = x[lag:] - x[lag:].mean()
    denom = (np.sqrt((a ** 2).sum()) * np.sqrt((b ** 2).sum()))
    if denom == 0:
        return 0.0
    return float((a * b).sum() / denom)


def _resource_features(rid: str, group: pd.DataFrame, account_id: str) -> dict:
    events = group[group["signal_type"] == "cloudtrail_event"]
    cost = group[group["signal_type"] == "cost"].sort_values("timestamp")

    if len(events) > 0:
        event_count = int(len(events))
        unique_users = events["user_identity"].nunique() if "user_identity" in events else 0
        unique_roles = events["iam_role"].nunique() if "iam_role" in events else 0
        hours = events["timestamp"].dt.hour
        peak_hour = int(hours.mode().iloc[0]) if len(hours) else 0
        weekday = events["timestamp"].dt.dayofweek
        weekend_ratio = float((weekday >= 5).mean()) if len(weekday) else 0.0
        cross_account = 0
        if "source_account" in events.columns:
            others = events["source_account"].dropna().astype(str)
            cross_account = int((others != account_id).any()) if len(others) else 0
    else:
        event_count = unique_users = unique_roles = peak_hour = 0
        weekend_ratio = 0.0
        cross_account = 0

    if len(cost) >= 3:
        y = cost["value"].astype(float).values
        x = np.arange(len(y), dtype=float)
        # OLS slope without bringing in scipy — y = a*x + b.
        slope = float(np.polyfit(x, y, 1)[0])
        variance = float(y.var())
        autocorr = _autocorr(y, lag=min(24, len(y) // 2))
    else:
        slope = variance = autocorr = 0.0

    return {
        "resource_id": rid,
        "event_count": event_count,
        "unique_users": unique_users,
        "peak_hour": peak_hour,
        "weekend_ratio": weekend_ratio,
        "unique_roles": unique_roles,
        "cross_account": cross_account,
        "cost_slope": slope,
        "cost_variance": variance,
        "cost_autocorr": autocorr,
    }


def extract_features(
    signals: pd.DataFrame,
    metadata: pd.DataFrame,
    account_id: str = "111111111111",
) -> pd.DataFrame:
    """Returns a DataFrame indexed by resource_id with FEATURE_COLUMNS as columns."""
    if signals.empty:
        return pd.DataFrame(columns=("resource_id",) + FEATURE_COLUMNS).set_index("resource_id")

    rows = []
    # Build features for every resource that has metadata, even if it has no signals
    # (zero-feature row is informative — "this thing exists but never gets touched").
    grouped = dict(tuple(signals.groupby("resource_id")))
    for rid in metadata["resource_id"]:
        group = grouped.get(rid, signals.iloc[0:0])
        rows.append(_resource_features(rid, group, account_id))

    df = pd.DataFrame(rows).set_index("resource_id")
    return df[list(FEATURE_COLUMNS)]


def normalize_features(features: pd.DataFrame) -> pd.DataFrame:
    """Z-score normalization. GNN training is much more stable on standardized inputs."""
    if features.empty:
        return features
    mu = features.mean()
    sigma = features.std().replace(0, 1)
    return (features - mu) / sigma
