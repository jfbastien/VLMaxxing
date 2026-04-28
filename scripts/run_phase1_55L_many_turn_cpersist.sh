#!/usr/bin/env bash
# Phase 1.55L — many-turn C-PERSIST horizon probe.

set -euo pipefail

cd "$(dirname "$0")/.."

PY="${PYTHON:-./.venv/bin/python}"
MODEL_PATH="${PHASE1_55L_MODEL_PATH:-$HOME/models/Qwen2.5-VL-7B-Instruct-4bit}"
OUT_DIR="${PHASE1_55L_OUT_DIR:-research/experiments/2026/artifacts/phase1_55L_many_turn_cpersist}"
VIDEO_IDS="${PHASE1_55L_VIDEO_IDS:-037,100,116,120,158,160,210}"
TURN_COUNTS="${PHASE1_55L_TURN_COUNTS:-10,20,50}"
POLICIES="${PHASE1_55L_POLICIES:-fixed_k1,adaptive_post_q2,refresh10}"
RSS_GUARD_MB="${RSS_GUARD_MB:-9000}"

if [[ -f "$OUT_DIR/summary.json" ]]; then
  echo "[1.55L] reusing complete artifact in $OUT_DIR"
  exit 0
fi
if [[ -d "$OUT_DIR" ]]; then
  echo "[1.55L] incomplete artifact directory exists; rerunning and overwriting JSONL outputs"
fi

"$PY" scripts/run_phase1_55L_many_turn_cpersist.py \
  --model-path "$MODEL_PATH" \
  --output-dir "$OUT_DIR" \
  --video-ids "$VIDEO_IDS" \
  --turn-counts "$TURN_COUNTS" \
  --policies "$POLICIES" \
  --frame-count "${PHASE1_55L_FRAME_COUNT:-20}" \
  --max-tokens "${PHASE1_55L_MAX_TOKENS:-32}" \
  --temperature "${PHASE1_55L_TEMPERATURE:-0.0}" \
  --top-p "${PHASE1_55L_TOP_P:-1.0}" \
  --min-p "${PHASE1_55L_MIN_P:-0.0}" \
  --seed "${PHASE1_55L_SEED:-42}" \
  --rss-guard-mb "$RSS_GUARD_MB"

echo "[1.55L] wrote $OUT_DIR/summary.json"
