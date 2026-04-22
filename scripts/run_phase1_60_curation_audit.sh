#!/usr/bin/env bash
# Phase 1.60 natural-corpus curation helper.
#
# Re-runs the cheap 1.57 feature-drift measurement on one or more VideoMME
# manifests, then ranks items by shifted-fraction so 1.60 can restart from a
# real candidate set instead of prose.
#
# Usage:
#   .venv/bin/bash scripts/run_phase1_60_curation_audit.sh

set -euo pipefail

cd "$(dirname "$0")/.."

PY="${PYTHON:-./.venv/bin/python}"
OUT_DIR="${PHASE1_60_OUT_DIR:-research/experiments/2026/artifacts/phase1_60_curation_audit}"
MODEL="${PHASE1_60_MODEL_PATH:-$HOME/models/Qwen2.5-VL-7B-Instruct-4bit}"
MANIFEST_DEV="research/benchmark_manifests/videomme_dev_v1.toml"
MANIFEST_HOLDOUT="research/benchmark_manifests/videomme_holdout_v1.toml"

mkdir -p "$OUT_DIR"

run_measure() {
  local frame_count="$1"
  "$PY" scripts/measure_feature_drift.py \
    --model qwen \
    --model-path "$MODEL" \
    --manifest "$MANIFEST_DEV" \
    --manifest "$MANIFEST_HOLDOUT" \
    --frame-count "$frame_count" \
    --output "$OUT_DIR/qwen_${frame_count}f_combined.json"
}

echo "[1.60] 8f shifted-fraction sweep"
run_measure 8

echo "[1.60] 16f shifted-fraction sweep"
run_measure 16

echo "[1.60] 32f shifted-fraction sweep"
run_measure 32

echo "[1.60] ranking candidates"
"$PY" scripts/build_phase1_60_scroll_pan_candidates.py \
  --summary "$OUT_DIR/qwen_8f_combined.json" \
  --summary "$OUT_DIR/qwen_16f_combined.json" \
  --summary "$OUT_DIR/qwen_32f_combined.json" \
  --top-k 20 \
  --min-shifted-fraction 0.30 \
  --selection-metric max \
  --json-out "$OUT_DIR/shifted_fraction_ranking.json" \
  --manifest-out "$OUT_DIR/scroll_pan_candidates.toml"
