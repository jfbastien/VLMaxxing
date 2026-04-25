#!/usr/bin/env bash
# Phase 1.55F-long — adaptive Q3 post-Q2 state on the long bucket.
#
# Why this exists:
# - 1.55F short showed the adaptive post-Q2-state policy is the best current
#   single-cell C-PERSIST result.
# - 1.55I showed fixed K=1 survives the same long tranche with zero observed
#   paired drift.
# - This is the direct test of whether the adaptive policy is truly three-regime.
#
# Runtime estimate on the fixed 7-clip long tranche:
# - session + baseline: ~50-65 min
# - paired analysis: <1 min

set -euo pipefail

cd "$(dirname "$0")/.."

PY="${PYTHON:-./.venv/bin/python}"
MODEL_PATH="${PHASE1_55F_LONG_MODEL_PATH:-$HOME/models/Qwen2.5-VL-7B-Instruct-4bit}"
OUT_DIR="${PHASE1_55F_LONG_OUT_DIR:-research/experiments/2026/artifacts/phase1_55F_long_adaptive_replication}"
VIDEO_IDS="${PHASE1_55F_LONG_VIDEO_IDS:-669,711,712,737,756,758,794}"
RSS_GUARD_MB="${RSS_GUARD_MB:-9000}"

mkdir -p "$OUT_DIR"

if [[ -f "$OUT_DIR/session_k1_n7.jsonl" && -f "$OUT_DIR/baseline_k1_n7.jsonl" && -f "$OUT_DIR/summary_k1_n7.json" ]]; then
  echo "[1.55F-long] reusing existing run outputs in $OUT_DIR"
else
  if [[ -f "$OUT_DIR/session_k1_n7.jsonl" || -f "$OUT_DIR/baseline_k1_n7.jsonl" || -f "$OUT_DIR/summary_k1_n7.json" ]]; then
    echo "[1.55F-long] incomplete prior outputs detected in $OUT_DIR; rerunning and overwriting partial artifacts"
  fi
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
    --rss-guard-mb "$RSS_GUARD_MB" \
    --output-dir "$OUT_DIR"
fi

"$PY" scripts/analyze_selective_reprefill_pairs.py \
  --session-jsonl "$OUT_DIR/session_k1_n7.jsonl" \
  --baseline-jsonl "$OUT_DIR/baseline_k1_n7.jsonl" \
  --output "$OUT_DIR/pair_metrics_k1_n7.json" \
  --paired-queries "$OUT_DIR/paired_queries_k1_n7.jsonl" \
  --label phase1_55F_long_adaptive_replication
