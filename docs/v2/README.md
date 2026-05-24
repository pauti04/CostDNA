# docs/v2/ — the Phase 1 spec

This directory holds the spec for the v2 restructure of CostDNA, completed in
Phase 0 of the upgrade plan. The actual restructure work happens in Phase 1
and consumes these documents as input.

| File | Purpose | Status |
|---|---|---|
| `headline-copy.md` | Source of truth for tagline, pitch, hero, resume bullet, thesis | Drafted in Phase 0 |
| `readme-v2-outline.md` | Section-by-section spec for the new README | Drafted in Phase 0 |
| `demoted-and-kept.md` | What survives the cut, what gets demoted, what gets deleted | Drafted in Phase 0 |

## How to consume these in Phase 1

1. Read `demoted-and-kept.md` first — it tells you what stays and what goes
2. Read `readme-v2-outline.md` — that's the literal section spec for the rewrite
3. Read `headline-copy.md` — copy exact strings from here into the README

Do **not** improvise copy. Every wording decision is centralized in
`headline-copy.md`; if a sentence in the new README contradicts those rules,
it's a bug.

## Phase order

- [x] Phase 0 — scope decisions, repo metadata, this spec (1h)
- [ ] Phase 2 — node2vec baseline (10h; do this before Phase 1 so the new
      results table has real numbers)
- [ ] Phase 1 — README + landing page restructure to match this spec (12h)
- [ ] Phase 3 — limitations + thesis section (`docs/limitations.md`) (8h)
- [ ] Phase 4 — external user feedback (`docs/field-notes/`) (10h)
- [ ] Phase 5 — optional polish (calibration sweep, reproducibility script) (10h)

Total: ~50h to land the new identity end-to-end. The audit-story repo
description is already live (Phase 0 deliverable). Everything below that is
Phases 1–5.
