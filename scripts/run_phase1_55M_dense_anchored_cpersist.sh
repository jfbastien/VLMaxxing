#!/usr/bin/env bash
# Phase 1.55M — dense-answer-anchored prompt-variation C-PERSIST stress.
#
# This is not a human natural-dialogue benchmark. It is the controlled
# prompt-variation variant: turn k+1 injects the canonical dense answer from
# turn k into both dense and cached arms, and the driver hard-fails if paired
# prompt hashes diverge.

set -euo pipefail

cd "$(dirname "$0")/.."

PY="${PYTHON:-./.venv/bin/python}"
MODEL_PATH="${PHASE1_55M_MODEL_PATH:-$HOME/models/Qwen2.5-VL-7B-Instruct-4bit}"
OUT_DIR="${PHASE1_55M_OUT_DIR:-research/experiments/2026/artifacts/phase1_55M_dense_anchored_cpersist}"
VIDEO_IDS="${PHASE1_55M_VIDEO_IDS:-037,100,116,120,158,160,210}"
TURN_COUNTS="${PHASE1_55M_TURN_COUNTS:-20}"
POLICIES="${PHASE1_55M_POLICIES:-fixed_k1,adaptive_post_q2,refresh10}"
RSS_GUARD_MB="${RSS_GUARD_MB:-12000}"

if [[ -f "$OUT_DIR/summary.json" ]]; then
  if "$PY" scripts/validate_phase1_55l_summary.py \
    --summary "$OUT_DIR/summary.json" \
    --video-ids "$VIDEO_IDS" \
    --turn-counts "$TURN_COUNTS" \
    --policies "$POLICIES" \
    --prompt-variant-mode dense_anchored; then
    echo "[1.55M] reusing complete artifact in $OUT_DIR"
    exit 0
  fi
  echo "[1.55M] existing summary is stale or incomplete; rerunning"
fi
if [[ -d "$OUT_DIR" ]]; then
  echo "[1.55M] incomplete artifact directory exists; rerunning and overwriting JSONL outputs"
fi

"$PY" scripts/run_phase1_55L_many_turn_cpersist.py \
  --model-path "$MODEL_PATH" \
  --output-dir "$OUT_DIR" \
  --video-ids "$VIDEO_IDS" \
  --turn-counts "$TURN_COUNTS" \
  --policies "$POLICIES" \
  --frame-count "${PHASE1_55M_FRAME_COUNT:-20}" \
  --max-tokens "${PHASE1_55M_MAX_TOKENS:-32}" \
  --temperature "${PHASE1_55M_TEMPERATURE:-0.0}" \
  --top-p "${PHASE1_55M_TOP_P:-1.0}" \
  --min-p "${PHASE1_55M_MIN_P:-0.0}" \
  --seed "${PHASE1_55M_SEED:-42}" \
  --rss-guard-mb "$RSS_GUARD_MB" \
  --prompt-variant-mode dense_anchored

echo "[1.55M] wrote $OUT_DIR/summary.json"
