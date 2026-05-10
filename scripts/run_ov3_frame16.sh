#!/usr/bin/env bash
# OV-3 frame budget robustness: same n=20 manifest, frame_count=16.
# Sequential, all 4 codec sources. Tests whether codec→dense holds at 2x frame budget.

set -euo pipefail

cd "$(dirname "$0")/.."

PY="${OV3_PYTHON:-uv run python}"
MODEL_PATH="${OV3_MODEL_PATH:-$HOME/models/Qwen2.5-VL-7B-Instruct-4bit}"
MANIFEST_PATH="${OV3F16_MANIFEST:-research/benchmark_manifests/videomme_short_dev_holdout_v1_n20.toml}"
REFERENCE_SUMMARY="${OV3_REFERENCE_SUMMARY:-research/experiments/2026/artifacts/phase1_57/qwen_8f_dev30.json}"
OUT_BASE="${OV3F16_OUT_DIR:-research/experiments/2026/artifacts/phase1_29_onevision_dev_n20_short_f16}"
FRAME_COUNT="${OV3F16_FRAME_COUNT:-16}"
MAX_TOKENS="${OV3_MAX_TOKENS:-32}"
CALIBRATION_MODE="${OV3_CALIBRATION_MODE:-per-item}"
CALIBRATION_SOURCE="${OV3_CALIBRATION_SOURCE:-live-pixel}"

mkdir -p "$OUT_BASE"

SOURCES=(novel_coded motion residual fused)

START_TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
echo "[ov3f16] start $START_TS" | tee -a "$OUT_BASE/run.log"
echo "[ov3f16] model=$MODEL_PATH manifest=$MANIFEST_PATH frame_count=$FRAME_COUNT max_tokens=$MAX_TOKENS" \
  | tee -a "$OUT_BASE/run.log"

for SRC in "${SOURCES[@]}"; do
  SRC_DIR="$OUT_BASE/$SRC"
  mkdir -p "$SRC_DIR"
  CACHE_PATH="$SRC_DIR/precompute_cache.json"

  echo "[ov3f16] === source=$SRC starting $(date -u +%Y-%m-%dT%H:%M:%SZ) ===" \
    | tee -a "$OUT_BASE/run.log" "$SRC_DIR/run.log"

  EXTRA_ARGS=(--codec-score-source "$SRC")
  if [[ "$SRC" == "fused" ]]; then
    EXTRA_ARGS+=(--fusion-mode weighted --motion-weight 1.0 --residual-weight 1.0)
  fi

  ${PY} scripts/run_phase1_29_planner_accuracy_probe.py \
    --manifest "$MANIFEST_PATH" \
    --model-path "$MODEL_PATH" \
    --frame-count "$FRAME_COUNT" \
    --max-tokens "$MAX_TOKENS" \
    --calibration-mode "$CALIBRATION_MODE" \
    --calibration-source "$CALIBRATION_SOURCE" \
    --reference-summary "$REFERENCE_SUMMARY" \
    --output-path "$SRC_DIR/results.jsonl" \
    --summary-path "$SRC_DIR/summary.json" \
    --precompute-cache-path "$CACHE_PATH" \
    --allow-dirty \
    "${EXTRA_ARGS[@]}" \
    2>&1 | tee -a "$SRC_DIR/run.log" "$OUT_BASE/run.log"

  echo "[ov3f16] === source=$SRC done $(date -u +%Y-%m-%dT%H:%M:%SZ) ===" \
    | tee -a "$OUT_BASE/run.log" "$SRC_DIR/run.log"
done

END_TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
echo "[ov3f16] end $END_TS" | tee -a "$OUT_BASE/run.log"
