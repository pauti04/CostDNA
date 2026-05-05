"""Time-varying simulator runner.

Different from `run_all.py` (which runs all teams 24/7). This one schedules
each team's workload to specific hours, giving each team a distinct
behavioral signature the GNN can learn:

  backend   weekdays 08:00–19:00     (business-hour traffic)
  data      every day 00:00–06:00    (overnight batch)
  ml        every day 21:00–02:00    (late-night training)
  platform  weekdays 06:00–22:00     (steady all-day support)

Run for 48+ hours. Result: `peak_hour`, `weekend_ratio`, `unique_users`,
and even `cost_*` (once Cost Explorer is populated) all become genuinely
distinguishing features.

Usage:
  python -m simulation.run_scheduled               # run forever, until Ctrl+C
  python -m simulation.run_scheduled --duration-hours 48
  python -m simulation.run_scheduled --once        # one-shot, just runs whoever is active right now
  python -m simulation.run_scheduled --tz UTC      # use UTC instead of system time
  python -m simulation.run_scheduled --interval 30 # iteration cadence in seconds
"""

from __future__ import annotations

import argparse
import logging
import signal
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from simulation import (backend_workload, data_workload, ml_workload,
                        platform_workload)

LOG_DIR = Path(__file__).resolve().parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

WORKLOADS = {
    "backend":  backend_workload.main,
    "data":     data_workload.main,
    "ml":       ml_workload.main,
    "platform": platform_workload.main,
}


def _is_active(team: str, now: datetime) -> bool:
    """Schedule each team's active hours. Local time of `now`."""
    hour = now.hour
    is_weekday = now.weekday() < 5

    if team == "backend":
        return is_weekday and 8 <= hour < 19
    if team == "data":
        return 0 <= hour < 6
    if team == "ml":
        # Wraps midnight: 21:00–02:00.
        return hour >= 21 or hour < 2
    if team == "platform":
        return is_weekday and 6 <= hour < 22
    return False


_stop = threading.Event()


def _on_signal(signum, frame) -> None:
    print(f"\nReceived signal {signum}; shutting down…")
    _stop.set()


def _setup_log() -> logging.Logger:
    log = logging.getLogger("sim.scheduled")
    log.setLevel(logging.INFO)
    log.handlers.clear()

    fh = logging.FileHandler(LOG_DIR / "scheduled.log", mode="a")
    fh.setFormatter(logging.Formatter("%(asctime)s  %(message)s"))
    log.addHandler(fh)

    sh = logging.StreamHandler()
    sh.setFormatter(logging.Formatter("[scheduled]  %(message)s"))
    log.addHandler(sh)
    return log


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--teams", default="backend,data,ml,platform",
                    help="Comma-separated teams to run.")
    ap.add_argument("--interval", type=int, default=60,
                    help="Seconds between iterations.")
    ap.add_argument("--duration-hours", type=float, default=None,
                    help="Auto-stop after N hours.")
    ap.add_argument("--tz", default=None,
                    help="Timezone (e.g. UTC, America/Los_Angeles). "
                         "Default: system local time.")
    ap.add_argument("--once", action="store_true",
                    help="Run currently-active team(s) once and exit.")
    args = ap.parse_args()

    teams = [t.strip() for t in args.teams.split(",") if t.strip()]
    invalid = [t for t in teams if t not in WORKLOADS]
    if invalid:
        print(f"unknown teams: {invalid}. choices: {list(WORKLOADS)}")
        sys.exit(1)

    tz = ZoneInfo(args.tz) if args.tz else None

    signal.signal(signal.SIGINT, _on_signal)
    signal.signal(signal.SIGTERM, _on_signal)

    log = _setup_log()
    log.info("starting (teams=%s, interval=%ds, tz=%s)",
             teams, args.interval, args.tz or "local")

    if args.once:
        now = datetime.now(tz=tz) if tz else datetime.now()
        active = [t for t in teams if _is_active(t, now)]
        log.info("now=%s active=%s", now.strftime("%a %H:%M"), active)
        for team in active:
            try:
                WORKLOADS[team]()
                log.info("%s: ok", team)
            except Exception as e:
                log.warning("%s: failed: %s", team, e)
        return

    deadline = (datetime.now() + timedelta(hours=args.duration_hours)
                if args.duration_hours else None)

    iteration = 0
    last_active_set: set = set()
    while not _stop.is_set():
        iteration += 1
        now = datetime.now(tz=tz) if tz else datetime.now()
        active = [t for t in teams if _is_active(t, now)]

        if set(active) != last_active_set:
            log.info("schedule shift @ %s — active: %s",
                     now.strftime("%a %H:%M"), active or "(none)")
            last_active_set = set(active)

        for team in active:
            try:
                WORKLOADS[team]()
            except Exception as e:
                log.warning("%s: failed: %s", team, e)

        if deadline and datetime.now() >= deadline:
            log.info("duration reached, stopping")
            break

        slept = 0
        while slept < args.interval and not _stop.is_set():
            time.sleep(min(1, args.interval - slept))
            slept += 1

    log.info("stopped after %d iterations", iteration)


if __name__ == "__main__":
    main()
