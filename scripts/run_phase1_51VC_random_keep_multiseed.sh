#!/usr/bin/env bash
# Phase 1.51VC random-keep robustness sweep.
#
# Runs the same matched Qwen 7B 8f VideoMME dev30 uniform_random baseline
# across a small seed set. This strengthens the sanity-baseline table without
# pretending uniform_random is a named peer method.
#
# Usage:
#   bash scripts/run_phase1_51VC_random_keep_multiseed.sh
set -euo pipefail
cd "$(dirname "$0")/.."

SEEDS="${PHASE1_51VC_SEEDS:-42 137 999 2024}"

for seed in $SEEDS; do
  echo "[1.51VC] random_keep seed=$seed"
  PHASE1_51VC_SCORE_SEED="$seed" bash scripts/run_phase1_51VC_random_keep_baseline.sh
done

echo "[1.51VC] rebuilding competitor-positioning snapshot/table"
"${PYTHON:-./.venv/bin/python}" scripts/build_competitor_positioning_table.py
