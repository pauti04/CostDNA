#!/usr/bin/env bash
#
# scripts/real-aws-test.sh — one-shot: stand up the labeled AWS env + start
# the simulators. Lets you generate ~5-7 days of real CloudTrail signal so
# you can run a real `costdna scan` and put a real-dollar number in the
# README.
#
# Pairs with scripts/real-aws-finish.sh (run after 5+ days).
#
# Cost: ~$25-35 for one week (3× t3.micro EC2, 1× small RDS, Lambda free
# tier, S3 pennies, CloudTrail $2/100k events, VPC Flow Logs ~$1).
# A $50 budget alarm is set as a guardrail.
#
# Prereqs: AWS CLI, terraform >=1.5, Python 3.11, costdna installed (`pip
# install -e .`), valid AWS profile with the policies in `costdna doctor`.

set -euo pipefail

# ---------- Inputs ----------
read -r -p "AWS profile to use [default]: " AWS_PROFILE
AWS_PROFILE=${AWS_PROFILE:-default}
export AWS_PROFILE

while :; do
  read -r -p "Email for the budget alert: " ALERT_EMAIL
  if [[ "$ALERT_EMAIL" =~ ^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$ ]]; then
    break
  fi
  echo "  that doesn't look like an email address. Try again."
done

read -r -p "Region [us-east-1]: " AWS_REGION
AWS_REGION=${AWS_REGION:-us-east-1}
export AWS_DEFAULT_REGION=$AWS_REGION

REPO_ROOT=$(cd "$(dirname "$0")/.." && pwd)

# Make sure the costdna CLI is installed before we go further (the script
# uses `costdna doctor` and `costdna scan`).
if ! command -v costdna >/dev/null 2>&1; then
  echo "  costdna CLI not on PATH. Installing editable from $REPO_ROOT…"
  (cd "$REPO_ROOT" && pip install -e ".[agent]" >/dev/null 2>&1) || {
    echo "  pip install failed. Run manually: cd $REPO_ROOT && pip install -e .[agent]"
    exit 1
  }
fi

echo
echo "→ profile:  $AWS_PROFILE"
echo "→ region:   $AWS_REGION"
echo "→ alert at: $ALERT_EMAIL (\$40 actual / \$50 hard cap)"
echo
read -r -p "Continue? (y/N): " CONFIRM
[ "$CONFIRM" = "y" ] || { echo "aborted."; exit 1; }

# ---------- 1. Preflight ----------
echo
echo "▸ [1/4] running costdna doctor — preflight permissions check"
costdna doctor --aws-profile "$AWS_PROFILE" --region "$AWS_REGION"

# ---------- 2. Budget alert ----------
echo
echo "▸ [2/4] setting AWS budget alarm at \$40 / \$50"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# idempotent: delete any prior alarm with the same name
aws budgets delete-budget \
  --account-id "$ACCOUNT_ID" \
  --budget-name "costdna-real-aws-test" 2>/dev/null || true

aws budgets create-budget \
  --account-id "$ACCOUNT_ID" \
  --budget '{
    "BudgetName": "costdna-real-aws-test",
    "BudgetLimit": {"Amount": "50", "Unit": "USD"},
    "TimeUnit": "MONTHLY",
    "BudgetType": "COST"
  }' \
  --notifications-with-subscribers "[
    {
      \"Notification\": {
        \"NotificationType\": \"ACTUAL\",
        \"ComparisonOperator\": \"GREATER_THAN\",
        \"Threshold\": 80,
        \"ThresholdType\": \"PERCENTAGE\"
      },
      \"Subscribers\": [{\"SubscriptionType\": \"EMAIL\", \"Address\": \"$ALERT_EMAIL\"}]
    }
  ]"

# ---------- 3. Terraform apply ----------
echo
echo "▸ [3/4] terraform apply — provisioning the labeled env"
cd "$REPO_ROOT/terraform"
terraform init -upgrade
terraform apply -auto-approve -var "region=$AWS_REGION"

# ---------- 4. Start the simulators ----------
echo
echo "▸ [4/4] starting simulators (run_scheduled.py — gives each team a"
echo "         distinct time-of-day fingerprint)"
cd "$REPO_ROOT"
mkdir -p simulation/logs

nohup python -m simulation.run_scheduled \
  --aws-profile "$AWS_PROFILE" \
  --region "$AWS_REGION" \
  > simulation/logs/scheduled.log 2>&1 &

SIM_PID=$!
echo "$SIM_PID" > simulation/logs/scheduled.pid

echo
echo "================================================================"
echo "  ✓ Setup complete."
echo "================================================================"
echo
echo "  Simulator PID:   $SIM_PID  (saved to simulation/logs/scheduled.pid)"
echo "  Simulator log:   simulation/logs/scheduled.log"
echo "  Budget alarm:    set for \$40 (alerts) / \$50 (hard cap)"
echo
echo "  → Wait 5-7 days for CloudTrail to accumulate signal."
echo "  → Then run:  bash scripts/real-aws-finish.sh"
echo
echo "  Sanity-check intermittently:"
echo "     tail -f simulation/logs/scheduled.log"
echo "     aws ce get-cost-and-usage --time-period Start=\$(date -v-2d +%F),End=\$(date +%F) --granularity DAILY --metrics BlendedCost"
echo
echo "  To stop the sim early:   kill \$(cat simulation/logs/scheduled.pid)"
echo "  To tear down everything: bash scripts/real-aws-finish.sh"
echo "================================================================"
