# leakcheck

**Catch label leakage before you report accuracy.** One function that finds
the columns in your dataset that deterministically encode the target — the
kind that make a model look like it learned something when it really just did
a database join.

```bash
pip install leakcheck
```

```python
import leakcheck

report = leakcheck.check(df, target="label")
if not report.clean:
    raise ValueError(f"leaking columns: {report.leaks}")
print(report)
```

```
leakcheck report — target: 'subscription_id'  (threshold 0.85)
  deployment_id            100.0%  (33205 distinct)  ⚠ LEAK
  cpu_bucket                 0.0%  (4 distinct)
  → LEAKING: deployment_id — drop these before reporting accuracy.
```

## Why this exists

I was training a graph model for cloud-resource attribution and hit **97%
accuracy** on Microsoft's published 2.6M-VM Azure dataset. Too good. One check:

```python
(df.groupby("deployment_id")["subscription_id"].nunique() == 1).mean()
# → 1.0
```

Across all **33,205 deployments**, every one mapped to exactly one
subscription. The graph edge I was using was a perfect lookup of the target.
The honest accuracy, with that edge removed, was **6.9%**.

I ran the same check on a second Microsoft dataset (Philly, 117K DL jobs) and
found the same shape: `user_id` was ~85% deterministic of the virtual cluster.
Two unrelated public datasets, same leak. The full write-up and the cloud-cost
project it came from: **[CostDNA](https://github.com/pauti04/CostDNA#the-audit)**.

`leakcheck` is that check, packaged so you can run it on anything.

## The check, precisely

For each candidate column, it computes **determinism** — the fraction of the
column's distinct values that map to exactly one target value:

```python
(df.groupby(column)[target].nunique() == 1).mean()
```

- `1.0` → the column is a perfect lookup of the target (a total leak).
- `0.85`+ → a partial leak (Philly's `user_id` was ~0.85). Still inflates
  accuracy, still worth dropping.
- `0.0` → the column genuinely spans multiple targets. Clean.

## API

```python
import leakcheck

# Batteries-included: audit every column, get a printable report
report = leakcheck.check(df, target="label")
report.clean          # bool
report.leaks          # {"deployment_id": 1.0, ...}

# Audit a specific subset
report = leakcheck.check(df, target="label", candidates=["a", "b", "c"])

# Low-level: the original two-line check as a function
leakcheck.find_deterministic_edges(df, "label", ["a", "b"], threshold=0.85)
# → {"a": 1.0}

# Single score
leakcheck.determinism_score(df, "a", "label")   # → 1.0
```

### CLI

```bash
leakcheck data.csv --target label                 # audit all columns
leakcheck data.csv --target label -c col_a col_b  # audit a subset
leakcheck data.csv --target label --fail-on-leak  # exit 1 if any leak (CI gate)
```

Drop `--fail-on-leak` into CI to block a benchmark PR that reintroduces a leak.

## When to run it

- Before reporting any accuracy on a new dataset.
- Before using a column as a **graph edge**, join key, or feature.
- On public benchmarks you didn't build — structural metadata (deployment
  IDs, user IDs, request IDs, machine assignments) is where leaks hide.

## Notes

- **High-cardinality columns** (nearly unique per row) will read as 1:1 by
  construction. `leakcheck` flags them separately (`⚠ high-cardinality — may
  be coincidental`) so you don't mistake a near-unique ID for a structural
  leak on a small sample.
- Only the columns you check are checked. An empty result means the
  candidates you passed are clean, not that the dataset is.
- Dependency-light: pandas + numpy.

## License

MIT.
