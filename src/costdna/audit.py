"""Dataset-leakage audit utilities.

Cloud-attribution datasets routinely contain columns that deterministically
encode the prediction target — e.g. on the published Microsoft Azure
2.6M-VM trace, every one of 33,205 deployments maps 1:1 to a single
subscription. Using such columns as graph edges or features produces
benchmark accuracies that look like "learning" but are really database
joins.

This module exposes a single function — :func:`find_deterministic_edges` —
that flags such columns before model training.

Example
-------

>>> import pandas as pd
>>> df = pd.DataFrame({
...     "deployment_id":   [1, 1, 2, 2, 3, 3],
...     "subscription_id": [10, 10, 20, 20, 30, 30],
...     "cpu_avg":         [0.4, 0.5, 0.6, 0.7, 0.8, 0.9],
... })
>>> find_deterministic_edges(df, target_col="subscription_id",
...                          candidate_edge_cols=["deployment_id", "cpu_avg"])
{'deployment_id': 1.0}

The function returns only edges with determinism ≥ ``threshold`` (default
0.85). Anything that comes back is leaking; either drop it from the graph
or treat the prediction task as a metadata lookup.

See ``docs/limitations.md`` (Appendix) and the blog post at
``docs/blog-post-audit.md`` for the full methodology and the Microsoft
Azure case study that motivated this check.
"""

from __future__ import annotations

import pandas as pd

__all__ = ["find_deterministic_edges", "AuditResult"]


from dataclasses import dataclass


@dataclass
class AuditResult:
    """Per-column determinism score returned by :func:`find_deterministic_edges`.

    Attributes
    ----------
    column : str
        The candidate edge / feature column under audit.
    determinism : float
        Fraction of distinct values of ``column`` that map to exactly one
        value of the target. ``1.0`` means the column is a perfect lookup
        of the target; anything ≥ the threshold is treated as a leak.
    n_distinct_values : int
        Number of distinct values of ``column``. Useful for context: a
        column with 2 distinct values reaching 1.0 determinism is far
        less suspicious than one with 33,205 values doing the same.
    """

    column: str
    determinism: float
    n_distinct_values: int


def find_deterministic_edges(
    df: pd.DataFrame,
    target_col: str,
    candidate_edge_cols: list[str],
    *,
    threshold: float = 0.85,
    return_full: bool = False,
) -> dict[str, float] | list[AuditResult]:
    """Identify edge / feature columns that deterministically encode the target.

    Parameters
    ----------
    df : pd.DataFrame
        The training dataset, with both ``target_col`` and every column in
        ``candidate_edge_cols`` present.
    target_col : str
        The prediction target. For cloud-attribution this is typically
        ``"subscription_id"``, ``"team"``, or ``"owner"``.
    candidate_edge_cols : list[str]
        Columns to audit. These are the columns the model will use as
        graph edges, structural features, or join keys — anything where
        a deterministic mapping to the target would inflate accuracy.
    threshold : float, default ``0.85``
        Minimum determinism to flag. ``1.0`` means the column is a perfect
        lookup; ``0.85`` is a useful default that catches both the 100%
        deterministic Azure ``deployment_id → subscription_id`` and the
        85% deterministic Philly ``user_id → vc`` patterns documented in
        the methodology audit.
    return_full : bool, default ``False``
        If ``False`` (default), return ``{column: determinism}`` for the
        compact dict the audit one-liner in the README produces. If
        ``True``, return a list of :class:`AuditResult` objects with the
        additional ``n_distinct_values`` context.

    Returns
    -------
    dict[str, float] | list[AuditResult]
        Columns that exceed ``threshold``, plus their determinism scores.
        An empty result means the dataset is clean for the candidates
        you asked about — but absence of evidence is not evidence of
        absence; only the columns you list are checked.

    Notes
    -----
    The cost of this function is :math:`O(n)` per column (one ``groupby``).
    Run it before reporting any cloud-attribution accuracy. The
    one-liner equivalent (no threshold, no labels) is::

        (df.groupby(col)[target_col].nunique() == 1).mean()

    See ``docs/blog-post-audit.md`` for the case study where this check
    turned a 97% benchmark into a 6.9% honest result on Microsoft's
    published 2.6M-VM Azure trace.
    """
    if target_col not in df.columns:
        raise KeyError(
            f"target_col {target_col!r} not in DataFrame columns "
            f"(got {list(df.columns)})"
        )

    results: list[AuditResult] = []
    for col in candidate_edge_cols:
        if col not in df.columns:
            raise KeyError(f"candidate column {col!r} not in DataFrame")
        if col == target_col:
            # A column is always perfectly deterministic of itself; this is
            # not a useful audit signal. Skip silently — the user almost
            # certainly didn't mean to ask about the target itself.
            continue
        per_edge_target_count = df.groupby(col)[target_col].nunique()
        determinism = float((per_edge_target_count == 1).mean())
        results.append(
            AuditResult(
                column=col,
                determinism=determinism,
                n_distinct_values=int(per_edge_target_count.size),
            )
        )

    flagged = [r for r in results if r.determinism >= threshold]
    if return_full:
        return sorted(flagged, key=lambda r: r.determinism, reverse=True)
    return {r.column: r.determinism for r in sorted(
        flagged, key=lambda r: r.determinism, reverse=True
    )}
