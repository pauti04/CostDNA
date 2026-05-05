"""Single-command launcher for all team simulators.

Replaces the 3-terminal dance with one process that spawns each simulator on
its own thread, in its own loop. One Ctrl+C cleanly stops everything.

Usage:
  python -m simulation.run_all
  python -m simulation.run_all --teams backend,data,ml --duration-hours 12
  python -m simulation.run_all --interval 30   # faster cadence

Logs go to simulation/logs/<team>.log and are tailed to stdout with a prefix.
"""

from __future__ import annotations

import argparse
import logging
import signal
import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

from simulation import (backend_workload, data_workload, ml_workload,
                        platform_workload)

LOG_DIR = Path(__file__).resolve().parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

WORKLOADS = {
    "backend":  (backend_workload.main,  60),
    "data":     (data_workload.main,     90),
    "ml":       (ml_workload.main,       120),
    "platform": (platform_workload.main, 180),
}

# Coordinated shutdown.
_stop = threading.Event()


def _setup_logging(team: str) -> logging.Logger:
    log = logging.getLogger(f"sim.{team}")
    log.setLevel(logging.INFO)
    log.handlers.clear()  # idempotent across re-imports

    fh = logging.FileHandler(LOG_DIR / f"{team}.log", mode="a")
    fh.setFormatter(logging.Formatter("%(asctime)s  %(message)s"))
    log.addHandler(fh)

    sh = logging.StreamHandler()
    sh.setFormatter(logging.Formatter(f"[{team:>8s}]  %(message)s"))
    log.addHandler(sh)
    return log


def _runner(team: str, fn, default_interval: int, interval: int) -> None:
    log = _setup_logging(team)
    log.info("starting (interval=%ds)", interval)
    iteration = 0
    while not _stop.is_set():
        iteration += 1
        try:
            fn()
            log.info("iter %d ok", iteration)
        except KeyboardInterrupt:
            break
        except Exception as e:
            log.warning("iter %d failed: %s", iteration, e)
        # Sleep responsively so Ctrl+C is fast.
        slept = 0
        while slept < interval and not _stop.is_set():
            time.sleep(min(1, interval - slept))
            slept += 1
    log.info("stopped")


def _on_signal(signum, frame) -> None:
    print(f"\nReceived signal {signum}; shutting down all simulators…")
    _stop.set()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--teams", default="backend,data,ml,platform",
                    help="Comma-separated teams to run.")
    ap.add_argument("--interval", type=int, default=None,
                    help="Override default sleep between iterations (seconds).")
    ap.add_argument("--duration-hours", type=float, default=None,
                    help="Auto-stop after N hours. Default: run until Ctrl+C.")
    args = ap.parse_args()

    teams = [t.strip() for t in args.teams.split(",") if t.strip()]
    invalid = [t for t in teams if t not in WORKLOADS]
    if invalid:
        print(f"unknown teams: {invalid}. choices: {list(WORKLOADS)}")
        sys.exit(1)

    signal.signal(signal.SIGINT, _on_signal)
    signal.signal(signal.SIGTERM, _on_signal)

    print(f"Launching {len(teams)} simulator(s): {teams}")
    print(f"Logs: {LOG_DIR}")
    if args.duration_hours:
        print(f"Auto-stop in {args.duration_hours}h")
    print()

    threads = []
    for team in teams:
        fn, default_interval = WORKLOADS[team]
        interval = args.interval if args.interval else default_interval
        t = threading.Thread(target=_runner, args=(team, fn, default_interval, interval),
                             daemon=True, name=f"sim-{team}")
        t.start()
        threads.append(t)

    deadline = (datetime.now() + timedelta(hours=args.duration_hours)
                if args.duration_hours else None)
    try:
        while not _stop.is_set():
            if deadline and datetime.now() >= deadline:
                print(f"\nDuration reached ({args.duration_hours}h); shutting down.")
                _stop.set()
                break
            time.sleep(1)
    except KeyboardInterrupt:
        _on_signal(signal.SIGINT, None)

    for t in threads:
        t.join(timeout=10)
    print("All simulators stopped.")


if __name__ == "__main__":
    main()
