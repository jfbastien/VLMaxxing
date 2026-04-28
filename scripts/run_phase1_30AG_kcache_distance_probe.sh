#!/usr/bin/env bash
# Phase 1.30AG — K/V cache-distance mechanism probe.

set -euo pipefail

cd "$(dirname "$0")/.."

PY="${PYTHON:-./.venv/bin/python}"
MODEL_PATH="${PHASE1_30AG_MODEL_PATH:-$HOME/models/Qwen2.5-VL-7B-Instruct-4bit}"
OUT_DIR="${PHASE1_30AG_OUT_DIR:-research/experiments/2026/artifacts/phase1_30AG_kcache_distance_probe}"

if [[ -f "$OUT_DIR/kcache_distance_summary.json" ]]; then
  echo "[1.30AG] reusing complete artifact in $OUT_DIR"
  exit 0
fi
if [[ -d "$OUT_DIR" ]]; then
  echo "[1.30AG] incomplete artifact directory exists; rerunning and overwriting outputs"
fi

"$PY" scripts/run_phase1_30AG_kcache_distance_probe.py \
  --model-path "$MODEL_PATH" \
  --output-dir "$OUT_DIR" \
  --max-pairs "${PHASE1_30AG_MAX_PAIRS:-20}" \
  --vision-tower-layer "${PHASE1_30AG_LAYER:-2}" \
  --vision-tower-keep-rate "${PHASE1_30AG_KEEP_RATE:-0.50}" \
  --seed "${PHASE1_30AG_SEED:-42}"

echo "[1.30AG] wrote $OUT_DIR/kcache_distance_summary.json"
