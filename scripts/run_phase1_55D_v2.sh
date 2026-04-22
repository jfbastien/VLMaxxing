#!/usr/bin/env bash
# Phase 1.55D v2 selective re-prefill runner.
#
# Usage:
#   .venv/bin/bash scripts/run_phase1_55D_v2.sh

set -euo pipefail

cd "$(dirname "$0")/.."

PY="${PYTHON:-./.venv/bin/python}"
MODEL_PATH="${PHASE1_55D_MODEL_PATH:-$HOME/models/Qwen2.5-VL-7B-Instruct-4bit}"
VIDEO_IDS="${PHASE1_55D_VIDEO_IDS:-037,100,116,120,158,160,210}"
FRAME_COUNT="${PHASE1_55D_FRAME_COUNT:-20}"
MAX_TOKENS="${PHASE1_55D_MAX_TOKENS:-32}"
REPREFILL_K="${PHASE1_55D_REPREFILL_K:-4}"
MODE="${PHASE1_55D_MODE:-both}"
OUT_DIR="${PHASE1_55D_OUT_DIR:-research/experiments/2026/artifacts/phase1_55D_selective_reprefill_v2}"

mkdir -p "$OUT_DIR"

"$PY" scripts/run_kv_selective_reprefill_v2.py \
  --mode "$MODE" \
  --video-ids "$VIDEO_IDS" \
  --frame-count "$FRAME_COUNT" \
  --reprefill-k "$REPREFILL_K" \
  --max-tokens "$MAX_TOKENS" \
  --model-path "$MODEL_PATH" \
  --output-dir "$OUT_DIR"
