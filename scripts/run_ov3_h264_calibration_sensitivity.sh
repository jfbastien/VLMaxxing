#!/usr/bin/env bash
# OV-3 H.264 calibration-sensitivity check.
#
# Baseline OV-3 used per-item live-pixel share matching. This run tests whether
# the H.264 Track A signal survives pooled threshold calibration at frame_count=8.

set -euo pipefail
LAST_ARM=""
trap 'echo "[ov3-calib] source $LAST_ARM failed at $(date -u +%Y-%m-%dT%H:%M:%SZ)"' ERR

cd "$(dirname "$0")/.."

PY="${OV3C_PYTHON:-uv run python}"
MODEL_PATH="${OV3C_MODEL_PATH:-$HOME/models/Qwen2.5-VL-7B-Instruct-4bit}"
MANIFEST_PATH="${OV3C_MANIFEST:-research/benchmark_manifests/videomme_short_present_v1_n57.toml}"
REFERENCE_SUMMARY="${OV3C_REFERENCE_SUMMARY:-research/experiments/2026/artifacts/phase1_57/qwen_8f_dev30.json}"
OUT_BASE="${OV3C_OUT_DIR:-research/experiments/2026/artifacts/phase1_29_onevision_n57_pooled_calibration}"
FRAME_COUNT="${OV3C_FRAME_COUNT:-8}"
MAX_TOKENS="${OV3C_MAX_TOKENS:-32}"
CALIBRATION_MODE="${OV3C_CALIBRATION_MODE:-pooled}"
CALIBRATION_SOURCE="${OV3C_CALIBRATION_SOURCE:-live-pixel}"
SOURCES=(${OV3C_SOURCES:-novel_coded motion residual fused})

mkdir -p "$OUT_BASE"

echo "[ov3-calib] manifest=$MANIFEST_PATH calibration=$CALIBRATION_MODE/$CALIBRATION_SOURCE"

for SRC in "${SOURCES[@]}"; do
  SRC_DIR="$OUT_BASE/$SRC"
  if [[ -f "$SRC_DIR/summary.json" ]]; then
    echo "[ov3-calib] === source=$SRC SKIP (already done) ==="
    continue
  fi
  mkdir -p "$SRC_DIR"
  CACHE_PATH="$SRC_DIR/precompute_cache.json"
  LAST_ARM="$SRC"
  echo "[ov3-calib] === source=$SRC starting $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="

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
    2>&1 | tee "$SRC_DIR/run.log"

  echo "[ov3-calib] === source=$SRC done $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
done
