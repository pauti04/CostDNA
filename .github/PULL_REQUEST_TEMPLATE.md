## What this changes

Brief description of the change and why.

Closes #(issue) <!-- if applicable -->

## Type

- [ ] Bug fix
- [ ] New feature
- [ ] Docs
- [ ] Collector live-validation (flipping a ⚠ to ✅)
- [ ] Refactor / tooling

## Checklist

- [ ] `python -m pytest tests/ -q` passes
- [ ] `ruff check src/ tests/` is clean
- [ ] `cd web && npx vitest run` passes (if `web/` touched)
- [ ] `cd web && npm run build` succeeds (if `web/` touched)
- [ ] New behaviour has a test
- [ ] No secrets / real AWS account IDs in the diff

## If this PR reports any accuracy number

CostDNA's whole thesis is that cloud-attribution datasets leak labels.
Any accuracy claim must be preceded by the leakage audit:

- [ ] I ran `costdna.audit.find_deterministic_edges` on the dataset
- [ ] No candidate column exceeds the determinism threshold (or the
      leaking columns are excluded and documented)
- [ ] N/A — this PR makes no accuracy claim

## Notes for reviewers

Anything non-obvious, tradeoffs you made, things you're unsure about.
