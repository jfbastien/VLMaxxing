#!/usr/bin/env bash
# Phase 1.57G — Gemma matched-duration feature-drift grid.
#
# Prior Gemma drift evidence was long-bucket focused. This mirrors the Qwen
# duration split across short/medium/long so the cross-architecture mechanism
# story has comparable drift geometry instead of only aggregate answer transfer.

set -euo pipefail

cd "$(dirname "$0")/.."

PY="${PYTHON:-./.venv/bin/python}"
MODEL_PATH="${GEMMA_MODEL_PATH:-$HOME/models/gemma-4-e4b-it-4bit}"
MANIFEST="${PHASE1_57G_MANIFEST:-research/benchmark_manifests/videomme_dev_v1.toml}"
OUT_DIR="${PHASE1_57G_OUT_DIR:-research/experiments/2026/artifacts/phase1_57G_gemma_matched_duration_drift}"

if [[ ! -e "$MODEL_PATH" ]]; then
  echo "missing Gemma model path: $MODEL_PATH" >&2
  exit 1
fi

mkdir -p "$OUT_DIR"

for GROUP in short medium long; do
  for FRAME_COUNT in 8 16 32; do
    OUT="$OUT_DIR/gemma_${FRAME_COUNT}f_${GROUP}.json"
    if [[ -f "$OUT" ]]; then
      echo "[1.57G] reusing $OUT"
    else
      echo "[1.57G] Gemma ${FRAME_COUNT}f group=${GROUP}"
      "$PY" scripts/measure_feature_drift.py \
        --model gemma \
        --model-path "$MODEL_PATH" \
        --manifest "$MANIFEST" \
        --group "$GROUP" \
        --frame-count "$FRAME_COUNT" \
        --output "$OUT"
    fi
  done
done

"$PY" scripts/summarize_feature_drift_grid.py \
  --input-dir "$OUT_DIR" \
  --model gemma \
  --groups short medium long \
  --frame-counts 8 16 32 \
  --output "$OUT_DIR/summary.json"
