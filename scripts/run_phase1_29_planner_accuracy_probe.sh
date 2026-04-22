#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

PY="${PYTHON:-./.venv/bin/python}"
MODEL_PATH="${PHASE1_29_MODEL_PATH:-$HOME/models/Qwen2.5-VL-7B-Instruct-4bit}"
MANIFEST_PATH="${PHASE1_29_MANIFEST:-research/benchmark_manifests/videomme_dev_v1_short_only.toml}"
REFERENCE_SUMMARY="${PHASE1_29_REFERENCE_SUMMARY:-research/experiments/2026/artifacts/phase1_57/qwen_8f_dev30.json}"
OUT_DIR="${PHASE1_29_OUT_DIR:-research/experiments/2026/artifacts/phase1_29_planner_accuracy_probe}"
FRAME_COUNT="${PHASE1_29_FRAME_COUNT:-8}"
MAX_TOKENS="${PHASE1_29_MAX_TOKENS:-32}"
CALIBRATION_MODE="${PHASE1_29_CALIBRATION_MODE:-per-item}"
CALIBRATION_SOURCE="${PHASE1_29_CALIBRATION_SOURCE:-live-pixel}"

mkdir -p "$OUT_DIR"

"$PY" scripts/run_phase1_29_planner_accuracy_probe.py \
  --manifest "$MANIFEST_PATH" \
  --model-path "$MODEL_PATH" \
  --frame-count "$FRAME_COUNT" \
  --max-tokens "$MAX_TOKENS" \
  --calibration-mode "$CALIBRATION_MODE" \
  --calibration-source "$CALIBRATION_SOURCE" \
  --reference-summary "$REFERENCE_SUMMARY" \
  --output-path "$OUT_DIR/results.jsonl" \
  --summary-path "$OUT_DIR/summary.json" \
  "$@"
