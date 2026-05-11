#!/usr/bin/env bash
# OV-6 Track B codec_grid smoke pass on M3.
#
# Goal: validate the codec_grid wiring end-to-end and produce the first
# measured vision-stage timing rows for codec vs magnitude_norm vs
# uniform_random at a single keep-rate on 10 short VideoMME items.
#
# Six arms, sequential, single MLX run at a time:
#   1. Dense (no patch, keep_rate=1.0) — accuracy reference
#   2. magnitude_norm at keep_rate=0.5 — existing 1.51V default
#   3. uniform_random at keep_rate=0.5 — 1.51VC positioning baseline
#   4. codec_grid novel_coded at keep_rate=0.5 — OV-3 strongest source
#   5. codec_grid motion at keep_rate=0.5
#   6. codec_grid residual at keep_rate=0.5

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
echo "[ov6] start $START_TS" | tee -a "$OUT_BASE/run.log"
echo "[ov6] model=$MODEL_PATH manifest=$MANIFEST_PATH frame_count=$FRAME_COUNT keep_rate=$KEEP_RATE" \
  | tee -a "$OUT_BASE/run.log"

run_arm() {
  local label="$1"
  shift
  local arm_dir="$OUT_BASE/$label"
  mkdir -p "$arm_dir"
  echo "[ov6] === arm=$label starting $(date -u +%Y-%m-%dT%H:%M:%SZ) ===" \
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
  echo "[ov6] === arm=$label done $(date -u +%Y-%m-%dT%H:%M:%SZ) ===" \
    | tee -a "$OUT_BASE/run.log" "$arm_dir/run.log"
}

run_arm dense \
  --vision-tower-keep-rate 1.0

run_arm magnitude_norm_kr050 \
  --vision-tower-layer "$LAYER" \
  --vision-tower-keep-rate "$KEEP_RATE" \
  --score-mode magnitude_norm

run_arm uniform_random_kr050 \
  --vision-tower-layer "$LAYER" \
  --vision-tower-keep-rate "$KEEP_RATE" \
  --score-mode uniform_random

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
echo "[ov6] end $END_TS" | tee -a "$OUT_BASE/run.log"
