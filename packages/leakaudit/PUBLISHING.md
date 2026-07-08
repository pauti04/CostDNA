# Publishing leakaudit

The package is PyPI-ready: `python -m build` produces a valid sdist + wheel and
`twine check` passes. The name `leakaudit` was confirmed available on PyPI at
package-creation time — **re-check before you publish** (`pip index versions
leakaudit` or visit https://pypi.org/project/leakaudit/); if it's since been
taken, other confirmed-available names as of writing: `target-leakage`,
`targetleak`, `labelleak`, `leaksniff`.

---

## Option 1 — publish from this monorepo (fastest, 2 commands)

You need a PyPI account and an API token (https://pypi.org/manage/account/token/).

```bash
cd packages/leakaudit
python -m build                                   # → dist/*.tar.gz, dist/*.whl
python -m twine upload dist/*                      # paste token as password (user: __token__)
```

That's it — `pip install leakaudit` works worldwide within a minute.

Smoke-test the published package in a clean venv:

```bash
python -m venv /tmp/lv && /tmp/lv/bin/pip install leakaudit
/tmp/lv/bin/leakaudit --help
```

## Option 2 — split into its own repo (recommended for a real project)

A standalone repo gets its own stars, CI badge, and Show HN — worth more than
a subdirectory. The CI + publish workflows in `.github/workflows/` here only
run once this is a repo root (GitHub ignores nested workflow files).

```bash
# from the CostDNA repo root:
git subtree split --prefix=packages/leakaudit -b leakaudit-split
cd /tmp && git clone /Users/pauti/costdna --branch leakaudit-split leakaudit
cd leakaudit && rm -rf .git && git init && git add -A && git commit -m "leakaudit 0.1.0"
gh repo create pauti04/leakaudit --public --source=. --push
```

Then either publish manually (Option 1 commands) or set up **Trusted
Publishing** so a tag auto-publishes (no token in the repo):

1. On https://pypi.org → your project → Publishing → add a trusted publisher:
   owner `pauti04`, repo `leakaudit`, workflow `publish.yml`, environment `pypi`.
2. `git tag v0.1.0 && git push --tags` → `.github/workflows/publish.yml` builds
   and publishes automatically.

## Release checklist

- [ ] Re-confirm the name is free on PyPI
- [ ] Bump `version` in `pyproject.toml` + add a `CHANGELOG.md` entry
- [ ] `pytest -q` green
- [ ] `python -m build && python -m twine check dist/*` both pass
- [ ] `twine upload` (or push a tag if Trusted Publishing is set up)
- [ ] Smoke-test `pip install leakaudit` in a clean venv
- [ ] Update the CostDNA README link if the package moved to its own repo

## After it's live

- Add a PyPI badge to the README: `![PyPI](https://img.shields.io/pypi/v/leakaudit)`
- Show HN / r/MachineLearning: "leakaudit — catch label leakage in one line
  (found a 97%→6.9% leak in Microsoft's public Azure dataset)". A tiny utility
  with a real case study is the ideal small-launch shape.
- Cross-link from the CostDNA audit section.
