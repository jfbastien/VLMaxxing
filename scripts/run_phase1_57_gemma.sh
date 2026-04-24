#!/usr/bin/env bash
# Phase 1.57 — Gemma 4 feature-drift sweep.
#
# Default scope mirrors the preregistered long-bucket mechanism slice on
# VideoMME dev. Override PHASE1_57_GROUP if you need medium/short instead.

set -euo pipefail

cd "$(dirname "$0")/.."

PY="${PYTHON:-./.venv/bin/python}"
MODEL_PATH="${GEMMA_MODEL_PATH:-$HOME/models/gemma-4-e4b-it-4bit}"
MANIFEST="${PHASE1_57_MANIFEST:-research/benchmark_manifests/videomme_dev_v1.toml}"
GROUP="${PHASE1_57_GROUP:-long}"
OUT_DIR="${PHASE1_57_OUT_DIR:-research/experiments/2026/artifacts/phase1_57_gemma}"

if [ ! -e "$MODEL_PATH" ]; then
  echo "missing Gemma model path: $MODEL_PATH" >&2
  exit 1
fi

mkdir -p "$OUT_DIR"

for frame_count in 8 16 32; do
  echo "[1.57] Gemma ${frame_count}f group=${GROUP}"
  "$PY" scripts/measure_feature_drift.py \
    --model gemma \
    --model-path "$MODEL_PATH" \
    --manifest "$MANIFEST" \
    --group "$GROUP" \
    --frame-count "$frame_count" \
    --output "$OUT_DIR/gemma_${frame_count}f_${GROUP}.json"
done
