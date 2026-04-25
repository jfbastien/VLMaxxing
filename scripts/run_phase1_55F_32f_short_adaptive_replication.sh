#!/usr/bin/env bash
# Phase 1.55F-32f — adaptive Q3 post-Q2 state at the 32f short depth boundary.
#
# Why this exists:
# - 1.55F short established the adaptive repaired-state policy at 20f.
# - 1.55H showed fixed K=1 survives the 32f short boundary.
# - This is the direct depth × adaptive-policy test.
#
# Runtime estimate on the fixed 7-clip short tranche:
# - session + baseline: ~65-90 min
# - paired analysis: <1 min

set -euo pipefail

cd "$(dirname "$0")/.."

PY="${PYTHON:-./.venv/bin/python}"
MODEL_PATH="${PHASE1_55F_32F_MODEL_PATH:-$HOME/models/Qwen2.5-VL-7B-Instruct-4bit}"
OUT_DIR="${PHASE1_55F_32F_OUT_DIR:-research/experiments/2026/artifacts/phase1_55F_32f_short_adaptive_replication}"
VIDEO_IDS="${PHASE1_55F_32F_VIDEO_IDS:-037,100,116,120,158,160,210}"
RSS_GUARD_MB="${RSS_GUARD_MB:-9000}"

mkdir -p "$OUT_DIR"

if [[ -f "$OUT_DIR/session_k1_n7.jsonl" && -f "$OUT_DIR/baseline_k1_n7.jsonl" && -f "$OUT_DIR/summary_k1_n7.json" ]]; then
  echo "[1.55F-32f] reusing existing run outputs in $OUT_DIR"
else
  if [[ -f "$OUT_DIR/session_k1_n7.jsonl" || -f "$OUT_DIR/baseline_k1_n7.jsonl" || -f "$OUT_DIR/summary_k1_n7.json" ]]; then
    echo "[1.55F-32f] incomplete prior outputs detected in $OUT_DIR; rerunning and overwriting partial artifacts"
  fi
  "$PY" scripts/run_kv_selective_reprefill_v2.py \
    --mode both \
    --video-ids "$VIDEO_IDS" \
    --frame-count 32 \
    --max-tokens 32 \
    --reprefill-k 1 \
    --reprefill-k-q2 1 \
    --reprefill-k-q3 0 \
    --q3-cache-source post_q2_repaired \
    --model-path "$MODEL_PATH" \
    --rss-guard-mb "$RSS_GUARD_MB" \
    --output-dir "$OUT_DIR"
fi

"$PY" scripts/analyze_selective_reprefill_pairs.py \
  --session-jsonl "$OUT_DIR/session_k1_n7.jsonl" \
  --baseline-jsonl "$OUT_DIR/baseline_k1_n7.jsonl" \
  --output "$OUT_DIR/pair_metrics_k1_n7.json" \
  --paired-queries "$OUT_DIR/paired_queries_k1_n7.jsonl" \
  --label phase1_55F_32f_short_adaptive_replication
