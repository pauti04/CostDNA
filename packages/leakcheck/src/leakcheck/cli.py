"""Command-line interface: `leakcheck data.csv --target label`."""

from __future__ import annotations

import argparse
import sys

import pandas as pd

from leakcheck.core import check


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="leakcheck",
        description="Find columns that deterministically encode your target "
                    "(label leakage) before you report accuracy.",
    )
    p.add_argument("csv", help="Path to a CSV file.")
    p.add_argument("--target", "-t", required=True, help="Target/label column.")
    p.add_argument("--columns", "-c", nargs="*", default=None,
                   help="Candidate columns to audit (default: all others).")
    p.add_argument("--threshold", type=float, default=0.85,
                   help="Determinism threshold to flag (default 0.85).")
    p.add_argument("--fail-on-leak", action="store_true",
                   help="Exit 1 if any leak is found (for CI).")
    args = p.parse_args(argv)

    try:
        df = pd.read_csv(args.csv)
    except Exception as e:  # noqa: BLE001 — surface a clean message to the CLI user
        print(f"error: could not read {args.csv}: {e}", file=sys.stderr)
        return 2

    report = check(df, args.target, args.columns, threshold=args.threshold)
    print(report)

    if args.fail_on_leak and not report.clean:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
