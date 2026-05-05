#!/usr/bin/env bash
# Bootstrap script — run once before pushing CostDNA to public GitHub.
#
# Usage:
#   scripts/init-github.sh <your-github-username>
#
# What it does:
#   1. Replaces all `yourname` placeholders with your actual handle
#   2. Initializes git, makes the initial commit, tags v0.1.0
#   3. Prints the exact commands to push + activate GitHub Pages

set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "usage: $0 <github-username>"
  exit 1
fi
USER="$1"

cd "$(dirname "$0")/.."

# 1. Replace placeholder.
echo "→ Replacing 'yourname' with '$USER' in docs/index.html …"
sed -i '' "s|yourname|$USER|g" docs/index.html

# Sanity check.
if grep -q yourname docs/index.html; then
  echo "  ✗ some 'yourname' references remain — bailing"
  exit 1
fi
echo "  ✓ done"

# 2. Initialize git.
if [ -d .git ]; then
  echo "→ git repo already exists — skipping init"
else
  echo "→ git init"
  git init -q
  git branch -M main
fi

# 3. Stage everything (respects .gitignore — data/ and runs/ are excluded).
git add -A
git status --short

# 4. First commit.
if git rev-parse HEAD >/dev/null 2>&1; then
  echo "→ commits already exist — skipping initial commit"
else
  git commit -q -m "Initial release — CostDNA v0.1.0

Open-source CLI that infers AWS team ownership from behavioral fingerprints
using a 4-layer GraphSAGE GNN. Validated on three production-scale public
cloud datasets (Microsoft Azure 2.6M VMs, Microsoft Philly 117K DL jobs,
Alibaba 71K containers) plus a synthetic AWS environment.

Methodological finding: across the three real datasets, structural metadata
(deployment_id on Azure, user_id on Philly, machine co-location on Alibaba)
dominates real-cloud attribution. Caught label-leakage bugs in two of three
datasets via self-audit.

See CHANGELOG.md for the full release notes."
  git tag -a v0.1.0 -m "v0.1.0 — Initial release"
  echo "  ✓ committed and tagged v0.1.0"
fi

cat <<EOF

──────────────────────────────────────────────────────────────────
  Next steps:
──────────────────────────────────────────────────────────────────

  1. Create the repo on GitHub:
       https://github.com/new
     Name: costdna
     Description: Behavioral GNN for cloud cost attribution
     Public, no README/license (we have those).

  2. Push:
       git remote add origin git@github.com:$USER/costdna.git
       git push -u origin main
       git push --tags

  3. Activate GitHub Pages:
       Repo → Settings → Pages → Source: "Deploy from a branch"
       Branch: main, Folder: /docs
       Save. Site is live at:  https://$USER.github.io/costdna/

  4. (Optional) Submit to Hacker News:
       https://news.ycombinator.com/submit
       Title: "Show HN: CostDNA — finds which AWS team owns every resource"
       URL:   https://github.com/$USER/costdna
       Best time: Tuesday 8am ET.

EOF
