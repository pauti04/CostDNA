"""Microsoft Philly trace loader.

Converts Microsoft Research's published Philly cluster trace (DL training
jobs at Microsoft, 2017) into CostDNA's signals/metadata schema.

Source: https://github.com/msr-fiddle/philly-traces

Each row in `cluster_job_log` is one DL training job:
  - `vc`: virtual cluster ID — *real team-equivalent identifier*
  - `jobid`: unique job ID
  - `user`: user who submitted
  - `status`: Pass / Failed / Killed
  - `submitted_time`, `attempts[].start_time`, `attempts[].end_time`
  - `attempts[].detail[].ip`: machine that ran the attempt
  - `attempts[].detail[].gpus`: GPUs used

This is the right kind of dataset for the methodology — virtual clusters
correspond to real research teams, jobs share user IDs, machines are shared
across teams (so machine_id is a noisy signal, not a tautology).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)


def _parse_dt(s: str) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def _job_to_record(job: dict) -> dict:
    """Aggregate a Philly job into one row of metadata + features."""
    submitted = _parse_dt(job.get("submitted_time", ""))
    attempts = job.get("attempts") or []

    ips: set[str] = set()
    n_gpus = 0
    runtime_total = 0
    queue_time = 0
    first_start = None

    for a in attempts:
        start = _parse_dt(a.get("start_time", ""))
        end = _parse_dt(a.get("end_time", ""))
        if start and end:
            runtime_total += max(0, (end - start).total_seconds())
        if start and first_start is None:
            first_start = start
        for d in a.get("detail") or []:
            if d.get("ip"):
                ips.add(d["ip"])
            n_gpus += len(d.get("gpus") or [])

    if submitted and first_start:
        queue_time = max(0, (first_start - submitted).total_seconds())

    return {
        "resource_id": job["jobid"],
        "team": job.get("vc", ""),
        "user": job.get("user", ""),
        "status": job.get("status", "Unknown"),
        "n_attempts": len(attempts),
        "runtime_s": runtime_total,
        "queue_time_s": queue_time,
        "n_machines": len(ips),
        "n_gpus": n_gpus,
        "primary_machine": next(iter(ips), ""),  # used for graph edge
        "submitted_time": submitted.isoformat() if submitted else "",
    }


def load_philly_trace(
    job_log_path: str | Path,
    *,
    top_n_vcs: int = 10,
    max_jobs_per_vc: int = 200,
    seed: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Returns (signals, metadata, flows, deploys).

    Sampling: top-N virtual clusters by job count, up to N jobs per VC.
    """
    path = Path(job_log_path)
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Download with:\n"
            "  mkdir -p data/philly\n"
            "  curl -L -o data/philly/trace-data.tar.gz "
            "https://media.githubusercontent.com/media/msr-fiddle/philly-traces/"
            "master/trace-data.tar.gz\n"
            "  tar -xzf data/philly/trace-data.tar.gz -C data/philly/\n"
            "Then point this at trace-data/cluster_job_log."
        )

    log.info("loading %s", path)
    with open(path) as f:
        jobs = json.load(f)
    log.info("parsed %d jobs", len(jobs))

    records = [_job_to_record(j) for j in jobs]
    df = pd.DataFrame(records)
    log.info("aggregated to %d job records, %d distinct VCs",
             len(df), df["team"].nunique())

    top_vcs = df["team"].value_counts().head(top_n_vcs).index
    df = df[df["team"].isin(top_vcs)].copy()

    # Sample per VC.
    sampled = []
    for vc, group in df.groupby("team"):
        if len(group) > max_jobs_per_vc:
            sampled.append(group.sample(max_jobs_per_vc, random_state=seed))
        else:
            sampled.append(group)
    df = pd.concat(sampled, ignore_index=True)
    log.info("sampled to %d jobs across %d VCs",
             len(df), df["team"].nunique())

    # ---- Metadata ----
    metadata = pd.DataFrame({
        "resource_id": df["resource_id"].astype(str),
        "resource_type": "ml_job",
        "team": df["team"].astype(str),
        "kind": "clean",
        "iam_role": df["user"].astype(str),       # IAM-edge equivalent
        "vpc_cidr": df["primary_machine"].astype(str),  # VPC-edge equivalent
        "created_at": df["submitted_time"].astype(str),
    })

    # ---- Signals (numeric features as fake "cost" rows so feature extractor
    # picks them up). Each row carries one of the per-job features as a value.
    _rng = np.random.default_rng(seed)
    rows = []
    for _, r in df.iterrows():
        # Generate one synthetic hourly cost row using submitted_time anchor.
        anchor = _parse_dt(r["submitted_time"]) or datetime.now(timezone.utc)
        # Cost proxy = runtime × n_gpus (GPU-hours).
        cost = float(r["runtime_s"] / 3600.0) * max(1, int(r["n_gpus"]))
        rows.append({
            "resource_id": r["resource_id"],
            "signal_type": "cost",
            "value": cost,
            "timestamp": anchor.isoformat(),
        })
        # CloudTrail-style event for each attempt.
        for i in range(int(r["n_attempts"])):
            rows.append({
                "resource_id": r["resource_id"],
                "signal_type": "cloudtrail_event",
                "user_identity": r["user"],
                "iam_role": r["user"],
                "event_name": "JobAttemptStart",
                "source_account": "philly",
                "value": 1,
                "timestamp": anchor.isoformat(),
            })

    signals = pd.DataFrame(rows)
    if not signals.empty:
        signals["timestamp"] = pd.to_datetime(signals["timestamp"],
                                               format="ISO8601", utc=True)

    flows = pd.DataFrame()
    deploys = pd.DataFrame()
    return signals, metadata, flows, deploys
