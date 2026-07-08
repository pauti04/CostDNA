"""Core leakage detection.

Two levels of API:

- ``find_deterministic_edges`` — the original two-line check as a function:
  returns ``{column: determinism}`` for columns above a threshold.
- ``check`` — a convenience that audits *every* other column against the
  target and returns a rich :class:`LeakReport` you can print.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

__all__ = [
    "determinism_score",
    "find_deterministic_edges",
    "check",
    "ColumnLeak",
    "LeakReport",
]


def determinism_score(df: pd.DataFrame, column: str, target: str) -> float:
    """Fraction of ``column``'s distinct values that map to exactly one target.

    ``1.0`` means the column is a perfect lookup of the target (a total leak);
    ``0.0`` means every value of the column spans multiple targets. This is the
    core measurement — everything else is thresholding and presentation.

        >>> (df.groupby(column)[target].nunique() == 1).mean()

    Empty groups (a column with no non-null values) score ``0.0``.
    """
    per_value_target_count = df.groupby(column, observed=True)[target].nunique()
    if per_value_target_count.size == 0:
        return 0.0
    return float((per_value_target_count == 1).mean())


def find_deterministic_edges(
    df: pd.DataFrame,
    target_col: str,
    candidate_edge_cols: list[str],
    *,
    threshold: float = 0.85,
) -> dict[str, float]:
    """Return candidate columns that deterministically encode the target.

    Parameters
    ----------
    df : pd.DataFrame
        The dataset.
    target_col : str
        The prediction target.
    candidate_edge_cols : list[str]
        Columns to audit — features, graph-edge keys, join keys.
    threshold : float, default 0.85
        Minimum determinism to flag. 1.0 catches total leaks (Azure's
        ``deployment_id``); 0.85 catches partial ones (Philly's ``user_id``,
        which was ~0.85 deterministic of the virtual cluster).

    Returns
    -------
    dict[str, float]
        ``{column: determinism}`` for flagged columns, highest first. Empty
        means the candidates you passed are clean — but only the columns you
        list are checked.
    """
    if target_col not in df.columns:
        raise KeyError(f"target_col {target_col!r} not in columns {list(df.columns)}")
    scores: dict[str, float] = {}
    for col in candidate_edge_cols:
        if col not in df.columns:
            raise KeyError(f"candidate column {col!r} not in DataFrame")
        if col == target_col:
            continue
        s = determinism_score(df, col, target_col)
        if s >= threshold:
            scores[col] = s
    return dict(sorted(scores.items(), key=lambda kv: kv[1], reverse=True))


@dataclass
class ColumnLeak:
    """One audited column's result."""

    column: str
    determinism: float
    n_distinct: int
    n_rows: int

    @property
    def is_leak(self) -> bool:
        return self.determinism >= 0.85

    @property
    def high_cardinality(self) -> bool:
        """True if the column is nearly unique per row — a 1:1 mapping can then
        be coincidence on a small sample rather than a structural leak."""
        return self.n_distinct > 0.8 * self.n_rows if self.n_rows else False


@dataclass
class LeakReport:
    """The result of :func:`check` — every audited column, sorted worst-first."""

    target: str
    columns: list[ColumnLeak] = field(default_factory=list)
    threshold: float = 0.85

    @property
    def leaks(self) -> dict[str, float]:
        """``{column: determinism}`` for columns at/above the threshold."""
        return {c.column: c.determinism for c in self.columns if c.determinism >= self.threshold}

    @property
    def clean(self) -> bool:
        return len(self.leaks) == 0

    def __str__(self) -> str:
        if not self.columns:
            return f"leakaudit: no columns audited against target {self.target!r}."
        lines = [f"leakaudit report — target: {self.target!r}  (threshold {self.threshold:.2f})"]
        for c in self.columns:
            flag = "  ⚠ LEAK" if c.determinism >= self.threshold else ""
            hc = "  (high-cardinality — may be coincidental)" if c.high_cardinality and c.determinism >= self.threshold else ""
            lines.append(
                f"  {c.column:<24} {c.determinism*100:5.1f}%  "
                f"({c.n_distinct} distinct){flag}{hc}"
            )
        if self.clean:
            lines.append("  → clean: no column exceeds the threshold.")
        else:
            worst = ", ".join(self.leaks)
            lines.append(f"  → LEAKING: {worst} — drop these before reporting accuracy.")
        return "\n".join(lines)


def check(
    df: pd.DataFrame,
    target: str,
    candidates: list[str] | None = None,
    *,
    threshold: float = 0.85,
) -> LeakReport:
    """Audit every column (or a given subset) against the target.

    This is the batteries-included entry point:

        >>> report = leakaudit.check(df, target="label")
        >>> if not report.clean:
        ...     raise ValueError(f"leaking columns: {report.leaks}")
        >>> print(report)

    If ``candidates`` is None, every column except the target is checked.
    """
    if target not in df.columns:
        raise KeyError(f"target {target!r} not in columns {list(df.columns)}")
    cols = candidates if candidates is not None else [c for c in df.columns if c != target]
    n_rows = len(df)
    results: list[ColumnLeak] = []
    for col in cols:
        if col not in df.columns:
            raise KeyError(f"candidate column {col!r} not in DataFrame")
        if col == target:
            continue
        det = determinism_score(df, col, target)
        results.append(
            ColumnLeak(
                column=col,
                determinism=det,
                n_distinct=int(df[col].nunique()),
                n_rows=n_rows,
            )
        )
    results.sort(key=lambda c: c.determinism, reverse=True)
    return LeakReport(target=target, columns=results, threshold=threshold)
