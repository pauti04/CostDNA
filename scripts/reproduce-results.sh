#!/usr/bin/env bash
# Reproduce every number in the README in one command.
#
# This script runs:
#   1. The full multi-seed benchmark on the synthetic env (Phase 2 results table)
#   2. The audit-check unit tests on the find_deterministic_edges() function
#   3. The decoy-kind validation (issue #6) that adversarial behaviour is
#      generated correctly
#   4. The synthetic env's calibration sweep
#   5. The full pytest suite (Python + audit + decoy + self-eval)
#
# Total runtime: ~3 minutes on a laptop. No network access required;
# everything operates on the synthetic env so anyone can reproduce
# without AWS, Azure, or GCP credentials.
#
# Outputs go to ./reproduce/ — gitignored, safe to delete.
#
# Usage:
#   bash scripts/reproduce-results.sh
#
# Reproduces from a clean clone:
#   git clone https://github.com/pauti04/CostDNA.git
#   cd CostDNA
#   pip install -e .
#   bash scripts/reproduce-results.sh

set -euo pipefail

cd "$(dirname "$0")/.."

mkdir -p reproduce

echo "============================================================"
echo "  CostDNA — full results reproduction"
echo "  Synthetic env, 5 seeds, GraphSAGE + node2vec + LR + k-NN +"
echo "  LabelProp + Majority baselines"
echo "============================================================"

echo
echo "[1/5] Running multi-seed synthetic benchmark..."
PYTHONPATH=src python scripts/bench-synthetic.py 2>&1 | tee reproduce/bench-output.txt

echo
echo "[2/5] Running unit tests for the audit module..."
PYTHONPATH=src python -m pytest tests/test_audit.py -v 2>&1 | tee reproduce/audit-tests.txt

echo
echo "[3/5] Validating decoy-kind generator (issue #6)..."
PYTHONPATH=src python -m pytest tests/test_pipeline.py::test_decoy_kind_is_generated_with_correct_metadata -v 2>&1 | tee reproduce/decoy-test.txt

echo
echo "[4/5] Self-eval module tests (issue #4)..."
PYTHONPATH=src python -m pytest tests/test_self_eval.py -v 2>&1 | tee reproduce/self-eval-tests.txt

echo
echo "[5/5] Full pytest suite..."
PYTHONPATH=src python -m pytest tests/ -v 2>&1 | tee reproduce/all-tests.txt

echo
echo "============================================================"
echo "  ✓ All artifacts in reproduce/"
echo
echo "  Output files:"
ls -1 reproduce/
echo
echo "  Compare reproduce/bench-output.txt against the synthetic env"
echo "  table in README section 'Controlled experiment — synthetic env'."
echo "  All numbers should match within ~3% (stochastic across seeds)."
echo "============================================================"
