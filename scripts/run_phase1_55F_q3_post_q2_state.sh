#!/usr/bin/env bash
# Phase 1.55F — Q3 from repaired post-Q2 state.
#
# Why this exists:
# - 1.55E showed that skipping Q3 refresh and falling back to the original
#   Q1 full-cache path re-enters the pathological basin.
# - The next falsifiable hypothesis is narrower: Q3 may be safe if it reuses
#   the repaired visual state produced by Q2, instead of reverting to Q1.
#
# Runtime estimate on the 7-clip short tranche:
# - session + baseline: ~60-75 min
# - paired analysis: <1 min

set -euo pipefail

cd "$(dirname "$0")/.."

PY="${PYTHON:-./.venv/bin/python}"
MODEL_PATH="${PHASE1_55F_MODEL_PATH:-$HOME/models/Qwen2.5-VL-7B-Instruct-4bit}"
OUT_DIR="${PHASE1_55F_OUT_DIR:-research/experiments/2026/artifacts/phase1_55F_q3_post_q2_state}"
VIDEO_IDS="${PHASE1_55F_VIDEO_IDS:-037,100,116,120,158,160,210}"

mkdir -p "$OUT_DIR"

if [[ -f "$OUT_DIR/session_k1_n7.jsonl" && -f "$OUT_DIR/baseline_k1_n7.jsonl" && -f "$OUT_DIR/summary_k1_n7.json" ]]; then
  echo "[1.55F] reusing existing run outputs in $OUT_DIR"
else
  "$PY" scripts/run_kv_selective_reprefill_v2.py \
    --mode both \
    --video-ids "$VIDEO_IDS" \
    --frame-count 20 \
    --max-tokens 32 \
    --reprefill-k 1 \
    --reprefill-k-q2 1 \
    --reprefill-k-q3 0 \
    --q3-cache-source post_q2_repaired \
    --model-path "$MODEL_PATH" \
    --output-dir "$OUT_DIR"
fi

"$PY" scripts/analyze_selective_reprefill_pairs.py \
  --session-jsonl "$OUT_DIR/session_k1_n7.jsonl" \
  --baseline-jsonl "$OUT_DIR/baseline_k1_n7.jsonl" \
  --output "$OUT_DIR/pair_metrics_k1_n7.json" \
  --label phase1_55F_q3_post_q2_state
