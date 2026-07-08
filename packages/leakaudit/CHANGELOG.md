# Changelog

## [0.1.0] — unreleased

First release.

- `find_deterministic_edges(df, target, candidates, threshold=0.85)` — the
  core check: which candidate columns deterministically encode the target.
- `check(df, target, candidates=None)` — audit every column, return a
  printable `LeakReport`.
- `determinism_score(df, column, target)` — the single measurement.
- `leakaudit` CLI with `--fail-on-leak` for CI gating.
- High-cardinality flagging so near-unique IDs aren't misread as structural
  leaks.
- Motivating case studies (Microsoft Azure 2.6M-VM, Philly 117K-job) in the
  README.
