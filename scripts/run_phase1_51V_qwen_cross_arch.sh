#!/usr/bin/env bash
# Phase 1.51V Qwen cross-architecture pair.
#
# Usage:
#   .venv/bin/bash scripts/run_phase1_51V_qwen_cross_arch.sh

set -euo pipefail

cd "$(dirname "$0")/.."

OUT="${PHASE1_51V_OUT_DIR:-research/experiments/2026/artifacts/phase1_51V_qwen_cross_arch}"
mkdir -p "$OUT"

PY="${PYTHON:-./.venv/bin/python}"
DRIVER="scripts/run_phase1_51V.py"
ANALYZE="scripts/analyze_phase1_51V_pair.py"
MANIFEST="${PHASE1_51V_MANIFEST:-research/benchmark_manifests/videomme_dev_v1.toml}"
N_ITEMS="${PHASE1_51V_N_ITEMS:-0}"
FRAME_COUNT="${PHASE1_51V_FRAME_COUNT:-8}"
MAX_TOKENS="${PHASE1_51V_MAX_TOKENS:-32}"
MODEL_PATH="${PHASE1_51V_MODEL_PATH:-$HOME/models/Qwen2.5-VL-7B-Instruct-4bit}"
RSS_GUARD_MB="${PHASE1_51V_RSS_GUARD_MB:-10000}"
VISION_TOWER_LAYER="${PHASE1_51V_VISION_TOWER_LAYER:-2}"
VISION_TOWER_KEEP_RATE="${PHASE1_51V_VISION_TOWER_KEEP_RATE:-0.50}"

run_arm() {
  local name="$1"; shift
  "$PY" "$DRIVER" \
    --manifest "$MANIFEST" \
    --n-items "$N_ITEMS" \
    --frame-count "$FRAME_COUNT" \
    --max-tokens "$MAX_TOKENS" \
    --model-path "$MODEL_PATH" \
    --rss-guard-mb "$RSS_GUARD_MB" \
    --output "$OUT/${name}.jsonl" \
    --summary "$OUT/${name}_summary.json" \
    --allow-dirty \
    "$@"
}

echo "[1.51V-Qwen] unpatched arm"
run_arm "videomme_dev30_8f_unpatched"

echo "[1.51V-Qwen] patched arm"
run_arm "videomme_dev30_8f_L2_kr050" \
  --vision-tower-layer "$VISION_TOWER_LAYER" \
  --vision-tower-keep-rate "$VISION_TOWER_KEEP_RATE"

echo "[1.51V-Qwen] analysis"
"$PY" "$ANALYZE" \
  --unpatched "$OUT/videomme_dev30_8f_unpatched_summary.json" \
  --patched "$OUT/videomme_dev30_8f_L2_kr050_summary.json" \
  > "$OUT/pair_analysis.txt"
