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
OUT="${PHASE1_51VC_OUT_DIR:-research/experiments/2026/artifacts/phase1_51VC_random_keep_baseline}"
FRAME_COUNT="${PHASE1_51VC_FRAME_COUNT:-8}"
VISION_TOWER_LAYER="${PHASE1_51VC_VISION_TOWER_LAYER:-2}"
# Keep this tag in sync with run_phase1_51VC_random_keep_baseline.sh output naming.
KR_TAG="${PHASE1_51VC_KR_TAG:-050}"

for seed in $SEEDS; do
  summary="$OUT/videomme_dev30_${FRAME_COUNT}f_L${VISION_TOWER_LAYER}_kr${KR_TAG}_uniform_random_seed${seed}_summary.json"
  if [[ -f "$summary" && "${PHASE1_51VC_FORCE:-0}" != "1" ]]; then
    echo "[1.51VC] skip existing random_keep seed=$seed ($summary)"
    continue
  fi
  echo "[1.51VC] random_keep seed=$seed"
  PHASE1_51VC_SCORE_SEED="$seed" bash scripts/run_phase1_51VC_random_keep_baseline.sh
done

echo "[1.51VC] rebuilding competitor-positioning snapshot/table"
"${PYTHON:-./.venv/bin/python}" scripts/build_competitor_positioning_table.py
