#!/usr/bin/env bash
# Phase 1.58 bf16 control runner.
#
# Usage:
#   QWEN_BF16_MODEL_PATH=~/models/Qwen2.5-VL-7B-Instruct \
#   .venv/bin/bash scripts/run_phase1_58_bf16_control.sh

set -euo pipefail

cd "$(dirname "$0")/.."

PY="${PYTHON:-./.venv/bin/python}"
FOURBIT_MODEL_PATH="${QWEN_4BIT_MODEL_PATH:-$HOME/models/Qwen2.5-VL-7B-Instruct-4bit}"
BF16_MODEL_PATH="${QWEN_BF16_MODEL_PATH:-$HOME/models/Qwen2.5-VL-7B-Instruct}"
MANIFEST="${PHASE1_58_MANIFEST:-research/benchmark_manifests/videomme_dev_v1.toml}"
OUT_DIR="${PHASE1_58_OUT_DIR:-research/experiments/2026/artifacts/phase1_58_bf16_control}"

if [ ! -e "$FOURBIT_MODEL_PATH" ]; then
  echo "missing 4bit model path: $FOURBIT_MODEL_PATH" >&2
  exit 1
fi

if [ ! -e "$BF16_MODEL_PATH" ]; then
  echo "missing bf16 model path: $BF16_MODEL_PATH" >&2
  exit 1
fi

mkdir -p "$OUT_DIR"

run_arm() {
  local precision="$1"
  local frame_count="$2"
  local model_path="$3"
  local stem="$OUT_DIR/${precision}_${frame_count}f"
  "$PY" scripts/run_benchmark_track_a.py run \
    --benchmark videomme \
    --manifest "$MANIFEST" \
    --frame-count "$frame_count" \
    --max-tokens 32 \
    --cache-mode identity \
    --model-path "$model_path" \
    --output-path "${stem}.jsonl" \
    --summary-path "${stem}_summary.json" \
    --no-feature-replay
}

echo "[1.58] 4bit 8f"
run_arm fourbit 8 "$FOURBIT_MODEL_PATH"

echo "[1.58] bf16 8f"
run_arm bf16 8 "$BF16_MODEL_PATH"

echo "[1.58] 4bit 16f"
run_arm fourbit 16 "$FOURBIT_MODEL_PATH"

echo "[1.58] bf16 16f"
run_arm bf16 16 "$BF16_MODEL_PATH"

echo "[1.58] analysis"
"$PY" scripts/analyze_phase1_58_bf16_control.py \
  --fourbit-8f "$OUT_DIR/fourbit_8f.jsonl" \
  --bf16-8f "$OUT_DIR/bf16_8f.jsonl" \
  --fourbit-16f "$OUT_DIR/fourbit_16f.jsonl" \
  --bf16-16f "$OUT_DIR/bf16_16f.jsonl" \
  --output "$OUT_DIR/analysis.json"
