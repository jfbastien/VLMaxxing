#!/usr/bin/env bash
# Phase 1.55I — K=1 selective re-prefill long-bucket replication.
#
# Why this exists:
# - 1.55D K=1 (short) and 1.55G K=1 (medium) both landed with zero observed
#   paired drift.
# - 1.55I is the natural third regime: can the same repaired K=1 policy survive
#   on long-bucket VideoMME at 20f, or is the current C-PERSIST envelope only
#   short+medium?
#
# Runtime estimate on the fixed 7-clip long tranche:
# - session + baseline: ~60-90 min
# - paired analysis: <1 min

set -euo pipefail

cd "$(dirname "$0")/.."

PY="${PYTHON:-./.venv/bin/python}"
MODEL_PATH="${PHASE1_55I_MODEL_PATH:-$HOME/models/Qwen2.5-VL-7B-Instruct-4bit}"
OUT_DIR="${PHASE1_55I_OUT_DIR:-research/experiments/2026/artifacts/phase1_55I_k1_long_replication}"
VIDEO_IDS="${PHASE1_55I_VIDEO_IDS:-669,711,712,737,756,758,794}"
RSS_GUARD_MB="${RSS_GUARD_MB:-9000}"

mkdir -p "$OUT_DIR"

if [[ -f "$OUT_DIR/session_k1_n7.jsonl" && -f "$OUT_DIR/baseline_k1_n7.jsonl" && -f "$OUT_DIR/summary_k1_n7.json" ]]; then
  echo "[1.55I] reusing existing run outputs in $OUT_DIR"
else
  if [[ -f "$OUT_DIR/session_k1_n7.jsonl" || -f "$OUT_DIR/baseline_k1_n7.jsonl" || -f "$OUT_DIR/summary_k1_n7.json" ]]; then
    echo "[1.55I] incomplete prior outputs detected in $OUT_DIR; rerunning and overwriting partial artifacts"
  fi
  "$PY" scripts/run_kv_selective_reprefill_v2.py \
    --mode both \
    --video-ids "$VIDEO_IDS" \
    --frame-count 20 \
    --max-tokens 32 \
    --reprefill-k 1 \
    --model-path "$MODEL_PATH" \
    --rss-guard-mb "$RSS_GUARD_MB" \
    --output-dir "$OUT_DIR"
fi

"$PY" scripts/analyze_selective_reprefill_pairs.py \
  --session-jsonl "$OUT_DIR/session_k1_n7.jsonl" \
  --baseline-jsonl "$OUT_DIR/baseline_k1_n7.jsonl" \
  --output "$OUT_DIR/pair_metrics_k1_n7.json" \
  --paired-queries "$OUT_DIR/paired_queries_k1_n7.jsonl" \
  --label phase1_55I_k1_long_replication
