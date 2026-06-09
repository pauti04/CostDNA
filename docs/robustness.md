# Robustness — how the model degrades under stress

Accuracy on a clean benchmark says little about a production deployment, where
the labels are noisy and the graph is incomplete. This is the honest
stress-test: two perturbation curves on the synthetic env, same trainer and
stratified split as `benchmark.py`, 3 seeds.

Reproduce: `PYTHONPATH=src python scripts/robustness_bench.py`
Perturbations + unit tests: `src/costdna/robustness.py`, `tests/test_robustness.py`.

## 1. Label noise (wrong seed labels)

Real ground-truth labels come from stale tags and tribal knowledge — they're
wrong some of the time. We flip X% of the *training* labels to a random wrong
class; the held-out test labels stay clean.

| Train-label noise | Test accuracy | vs. clean |
|---|---|---|
| 0%  | 96.0% ± 3.3% | baseline |
| 10% | 81.4% ± 10.6% | −15 pts |
| 20% | 75.1% ± 4.4% | −21 pts |
| 30% | 57.8% ± 5.6% | −38 pts |
| 40% | 61.7% ± 10.4% | −34 pts (noisy past 30%) |

**Reading:** the model tolerates ~10–20% label noise with graceful degradation,
then falls off past 30%. Roughly tracks "you keep what you can still learn from
the clean majority." The 40% point is within noise of 30% — on ~55 training
labels across 3 seeds the variance is large, so don't over-read the tail.
Practical takeaway: the active-learning loop (which confirms low-confidence
labels with a human) matters precisely because seed-label quality drives this
curve.

## 2. Edge dropout (incomplete graph)

Real accounts miss VPC flow logs, have partial IAM visibility, or throttle
CloudTrail — the graph is a subsample of the true one. We randomly keep X% of
edges; labels stay clean.

| Graph edges kept | Test accuracy | vs. full graph |
|---|---|---|
| 100% | 96.0% ± 3.3% | baseline |
| 75%  | 93.3% ± 5.0% | −3 pts |
| 50%  | 93.4% ± 1.8% | −3 pts |
| 25%  | 90.7% ± 5.0% | −5 pts |
| 0% (no graph) | 89.4% ± 6.8% | −7 pts |

**Reading — and an honest double-edged finding:** the model is *very* robust to
losing edges (only −7 pts with the graph entirely removed). That's good for
production (it doesn't need a complete graph). But it also means **on the clean
synthetic env the behavioral features carry almost all the signal, and the
graph adds only ~7 points on average.**

This is consistent with the project's central thesis rather than contradicting
it. The graph's value is not uniform — it concentrates on the *ambiguous* cases
(cross-team resources, decoys, shared services) where features alone point the
wrong way, and is near-zero on the clean majority. It's the same lesson as the
audit, from the other side:

- On the **leaky Azure benchmark**, graph structure did *too much* — a single
  deterministic edge was a perfect label lookup (the 97% tautology).
- On the **clean synthetic env**, graph structure does *little* on average —
  the features are already separable.
- The graph earns its place in the **hard middle**: real accounts where some
  resources are behaviorally ambiguous and the only disambiguating signal is
  who-talks-to-whom.

Honest implication: if your account's resources are behaviorally distinct, a
feature-only model (LogReg on the 17 behavioral features) gets you most of the
way. CostDNA's graph layer is worth its complexity specifically when you have
shared-service / cross-team / reassigned resources that features can't separate
— which is exactly the regime the synthetic env's hard-case kinds reproduce and
where the per-kind benchmark (`benchmark.py`) shows the graph methods pulling
ahead.

## Caveats

- Synthetic env only (~79 labeled nodes, 4 teams). The absolute numbers are
  high because the task is easy; the *shapes* of the curves are the point.
- 3 seeds → wide error bars, especially on the label-noise tail.
- Not measured on the real-AWS or Azure regimes (too few labels on real-AWS to
  bin; Azure full data not staged).
