"""leakaudit — catch label leakage before you report accuracy.

Cloud, tabular, and graph datasets routinely contain columns that
deterministically (or near-deterministically) encode the prediction target.
Using such a column as a feature or a graph edge produces benchmark accuracy
that looks like learning but is really a database join.

The public API:

    >>> import leakaudit
    >>> report = leakaudit.check(df, target="label")
    >>> report.leaks              # columns that encode the target
    >>> print(report)             # human-readable summary

Or the low-level function:

    >>> leakaudit.find_deterministic_edges(df, "label", ["col_a", "col_b"])
    {'col_a': 1.0}

Motivated by a real finding: on Microsoft's published 2.6M-VM Azure trace,
`deployment_id` mapped 1:1 to `subscription_id` across all 33,205 deployments,
inflating a benchmark to 97% that was honestly 6.9%. See the README.
"""

from leakaudit.core import (
    ColumnLeak,
    LeakReport,
    check,
    determinism_score,
    find_deterministic_edges,
)

__all__ = [
    "check",
    "find_deterministic_edges",
    "determinism_score",
    "LeakReport",
    "ColumnLeak",
]

__version__ = "0.1.0"
