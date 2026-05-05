#!/usr/bin/env bash
#
# scripts/real-aws-finish.sh — run after `real-aws-test.sh` has been live
# for 5-7 days. Stops the simulator, runs costdna scan against the real
# account, prints the executive summary panel, then tears the env down so
# you stop accruing spend.
#
# Output:
#   runs/real-aws-<DATE>/      — saved scan + executive summary
#   docs/images/real-aws-summary.png  — screenshot for the README

set -euo pipefail

REPO_ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$REPO_ROOT"

# ---------- Inputs ----------
read -r -p "AWS profile to use [default]: " AWS_PROFILE
AWS_PROFILE=${AWS_PROFILE:-default}
export AWS_PROFILE

read -r -p "Region [us-east-1]: " AWS_REGION
AWS_REGION=${AWS_REGION:-us-east-1}
export AWS_DEFAULT_REGION=$AWS_REGION

DATE_TAG=$(date +%F)
SAVE_DIR="runs/real-aws-$DATE_TAG"

echo "→ profile:    $AWS_PROFILE"
echo "→ region:     $AWS_REGION"
echo "→ save-dir:   $SAVE_DIR"
echo

# ---------- 1. Stop the simulator ----------
echo "▸ [1/4] stopping the background simulator"
if [ -f simulation/logs/scheduled.pid ]; then
  SIM_PID=$(cat simulation/logs/scheduled.pid)
  if kill -0 "$SIM_PID" 2>/dev/null; then
    kill "$SIM_PID"
    echo "  killed PID $SIM_PID"
  else
    echo "  PID $SIM_PID not running — already stopped"
  fi
  rm -f simulation/logs/scheduled.pid
else
  echo "  no PID file — nothing to stop"
fi

# ---------- 2. Run the scan ----------
echo
echo "▸ [2/4] running costdna scan — this can take 5-15 min"
echo "         (CloudTrail lookups are throttled; semantic features need GPU/CPU)"
mkdir -p "$SAVE_DIR"
costdna scan \
  --aws-profile "$AWS_PROFILE" \
  --region "$AWS_REGION" \
  --save-dir "$SAVE_DIR" \
  --show-kind \
  | tee "$SAVE_DIR/scan-output.txt"

# ---------- 3. Capture the executive summary as an image ----------
echo
echo "▸ [3/4] capturing the executive summary for the README"
# The Rich-formatted panel is in scan-output.txt; we need to render it as
# an image. The cleanest path: re-print just the summary using Rich's
# export, then convert via headless terminal. Easier: embed the text
# as a code block in the README. Skip the image for now and let the
# user paste the panel into a separate screenshot if they want.
echo "  → see $SAVE_DIR/scan-output.txt for the panel"
echo "  → take a terminal screenshot of it for the README if you want a visual"

# ---------- 4. Terraform destroy ----------
echo
echo "▸ [4/4] terraform destroy — tearing down to stop spend"
read -r -p "Confirm destroy? (y/N): " CONFIRM
if [ "$CONFIRM" = "y" ]; then
  cd "$REPO_ROOT/terraform"
  terraform destroy -auto-approve -var "region=$AWS_REGION"
  echo "  ✓ env destroyed. budget alarm left in place — delete manually if"
  echo "    you don't want it."
else
  echo "  skipped — REMEMBER to manually run 'cd terraform && terraform"
  echo "    destroy' when you're done. Idle RDS still costs money."
fi

cat <<EOF

================================================================
  ✓ Real-AWS deployment complete.

  Files:
     $SAVE_DIR/scan-output.txt        — full CLI output
     $SAVE_DIR/predictions.csv        — per-resource predictions
     $SAVE_DIR/executive-summary.txt  — exec panel only

  Next step: fill in the placeholders in the README's
  "Real AWS deployment" section using values from the scan output.
  Specifically:

     <RESOURCE_COUNT>   — total_resources from the summary
     <SPEND>            — total spend in USD
     <CONFIDENT>        — count at >=70% confidence
     <PCT>              — confident / total * 100

  Then: git commit, git push, README is updated.
================================================================
EOF
