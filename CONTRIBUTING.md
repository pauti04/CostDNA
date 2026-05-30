# Contributing to CostDNA

Thanks for considering a contribution. CostDNA is an open-source FinOps
input layer — it infers ownership of untagged AWS resources and writes
tags back. The bar for contributions is high in one specific way:
**we don't ship attribution numbers we haven't audited.** More on that
below.

## Ways to contribute

| You have | Do this |
|---|---|
| A bug | [Open a bug report](https://github.com/pauti04/CostDNA/issues/new?template=bug_report.md) |
| A feature idea | [Open a feature request](https://github.com/pauti04/CostDNA/issues/new?template=feature_request.md) |
| Ran it on a real account | [File a field note](https://github.com/pauti04/CostDNA/issues/new?template=field_note.md) — these are the most valuable thing you can give the project |
| A public cloud dataset with rich behavioural features and no structural leak | Open an issue — this is the missing data point the methodology needs |
| Code | Read the dev setup below, then open a PR |

## Dev setup

```bash
git clone https://github.com/pauti04/CostDNA.git
cd CostDNA
pip install -e '.[dev]'          # Python: pytest + ruff + everything
python -m pytest tests/ -q       # 32 tests, ~10s, no network/AWS needed

cd web
npm install
npx vitest run                   # 37 tests
npm run build                    # type-check + Next build
```

Everything runs offline against the synthetic environment — no AWS
account, no API keys, no network access required to develop or test.

## The quality bar: audit before you claim

The defining lesson of this project is that cloud-attribution datasets
routinely contain label leakage that inflates accuracy. See
[`docs/blog-post-audit.md`](docs/blog-post-audit.md) for the full story.

**If your PR reports any accuracy number on any dataset**, you must
run the leakage audit first:

```python
from costdna.audit import find_deterministic_edges

leaks = find_deterministic_edges(
    df, target_col="team",
    candidate_edge_cols=[c for c in df.columns if c != "team"],
)
assert not leaks, f"Leaking columns must be excluded before training: {leaks}"
```

A PR that reports "97% accuracy" without the audit will be asked to
run it. This isn't bureaucracy — it's the entire thesis of the
project. We'd rather ship an honest 6.9% than an inflated 97%.

## PR checklist

Before you open a PR:

- [ ] `python -m pytest tests/ -q` passes (32 tests)
- [ ] `ruff check src/ tests/` is clean
- [ ] `cd web && npx vitest run` passes (37 tests) — if you touched `web/`
- [ ] `cd web && npm run build` succeeds — if you touched `web/`
- [ ] New behaviour has a test
- [ ] Any accuracy claim is preceded by the leakage audit
- [ ] No secrets, API keys, or real AWS account IDs in the diff

## Code style

- **Python:** ruff-formatted, type hints on public functions, docstrings
  that explain *why* not just *what*. Match the existing tone in
  `src/costdna/` — comments explain the engineering tradeoff, not the
  obvious.
- **TypeScript:** the web app is Next.js + Tailwind. Keep components
  small; the audit-check library (`web/src/lib/audit-check.ts`) is
  intentionally a pure-JS port of the Python `find_deterministic_edges`
  — keep the two in sync if you change one.

## What gets merged fast

- Bug fixes with a regression test
- A live-validated cloud collector run (Azure/GCP — flip a ⚠ to ✅)
- A field note from running CostDNA on a real account
- Documentation that closes a gap a real user hit

## What gets discussed first

- New ML architectures (open an issue; the GNN choice is deliberate —
  see the GraphSAGE-vs-GAT-vs-node2vec rationale in the README)
- New product surfaces (the scope is intentionally "inferred tags input
  layer," not "another FinOps dashboard")
- Anything that adds an accuracy claim without an audit

## License

By contributing, you agree your contributions are licensed under the
[MIT License](LICENSE), same as the project.

## Security

Found a vulnerability? **Do not** open a public issue. See
[`SECURITY.md`](SECURITY.md).
