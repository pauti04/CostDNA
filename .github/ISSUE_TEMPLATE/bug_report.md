---
name: Bug report
about: Something broke or behaved unexpectedly
title: "[bug] "
labels: bug
---

## What happened

A clear description of the bug.

## What you expected

What should have happened instead.

## Reproduction

```bash
# The exact command(s) you ran
costdna scan --synthetic --show-kind
```

Minimal repro is best. If it involves a CSV, attach a redacted sample
(no real account IDs).

## Environment

- CostDNA version: (`pip show costdna` or commit SHA)
- Python version:
- OS:
- Install method: (pip / Docker / from source)
- Cloud: (synthetic / AWS / Azure / GCP)

## Logs / traceback

```
paste the full traceback here
```

## Anything else

Screenshots, related issues, what you've already tried.
