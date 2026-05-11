#!/usr/bin/env bash
# OV-6 Track B smoke continuation: run the three codec_grid arms only.
# The dense, magnitude_norm, and uniform_random arms were committed in the
# initial smoke pass; this script picks up after the merged-group geometry fix.

set -euo pipefail

cd "$(dirname "$0")/.."

PY="${OV6_PYTHON:-uv run python}"
MODEL_PATH="${OV6_MODEL_PATH:-$HOME/models/Qwen2.5-VL-7B-Instruct-4bit}"
MANIFEST_PATH="${OV6_MANIFEST:-research/benchmark_manifests/videomme_dev_v1_short_only.toml}"
OUT_BASE="${OV6_OUT_DIR:-research/experiments/2026/artifacts/phase1_51V_ov6_smoke}"
FRAME_COUNT="${OV6_FRAME_COUNT:-8}"
MAX_TOKENS="${OV6_MAX_TOKENS:-32}"
KEEP_RATE="${OV6_KEEP_RATE:-0.5}"
LAYER="${OV6_LAYER:-2}"

mkdir -p "$OUT_BASE"

START_TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
echo "[ov6c] start $START_TS" | tee -a "$OUT_BASE/run.log"

run_arm() {
  local label="$1"
  shift
  local arm_dir="$OUT_BASE/$label"
  mkdir -p "$arm_dir"
  echo "[ov6c] === arm=$label starting $(date -u +%Y-%m-%dT%H:%M:%SZ) ===" \
    | tee -a "$OUT_BASE/run.log" "$arm_dir/run.log"
  ${PY} scripts/run_phase1_51V.py \
    --manifest "$MANIFEST_PATH" \
    --model-path "$MODEL_PATH" \
    --frame-count "$FRAME_COUNT" \
    --max-tokens "$MAX_TOKENS" \
    --output "$arm_dir/results.jsonl" \
    --summary "$arm_dir/summary.json" \
    --allow-dirty \
    "$@" \
    2>&1 | tee -a "$arm_dir/run.log" "$OUT_BASE/run.log"
  echo "[ov6c] === arm=$label done $(date -u +%Y-%m-%dT%H:%M:%SZ) ===" \
    | tee -a "$OUT_BASE/run.log" "$arm_dir/run.log"
}

run_arm codec_novel_coded_kr050 \
  --vision-tower-layer "$LAYER" \
  --vision-tower-keep-rate "$KEEP_RATE" \
  --score-mode codec_grid \
  --codec-score-source novel_coded

run_arm codec_motion_kr050 \
  --vision-tower-layer "$LAYER" \
  --vision-tower-keep-rate "$KEEP_RATE" \
  --score-mode codec_grid \
  --codec-score-source motion

run_arm codec_residual_kr050 \
  --vision-tower-layer "$LAYER" \
  --vision-tower-keep-rate "$KEEP_RATE" \
  --score-mode codec_grid \
  --codec-score-source residual

END_TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
echo "[ov6c] end $END_TS" | tee -a "$OUT_BASE/run.log"
