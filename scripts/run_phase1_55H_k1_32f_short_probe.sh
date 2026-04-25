#!/usr/bin/env bash
# Phase 1.55H — K=1 selective re-prefill 32f short-bucket probe.
#
# Why this exists:
# - 1.55D K=1 is the best current local recovery point, but only at 20f.
# - 1.55H asks the next boundary question directly: does the same repaired
#   policy still hold after the 7B persistent-KV lane has crossed into the
#   known 32f long-context basin region?
#
# Runtime estimate on the 7-clip short tranche:
# - session + baseline: ~90-120 min
# - paired analysis: <1 min

set -euo pipefail

cd "$(dirname "$0")/.."

PY="${PYTHON:-./.venv/bin/python}"
MODEL_PATH="${PHASE1_55H_MODEL_PATH:-$HOME/models/Qwen2.5-VL-7B-Instruct-4bit}"
OUT_DIR="${PHASE1_55H_OUT_DIR:-research/experiments/2026/artifacts/phase1_55H_k1_32f_short_probe}"
VIDEO_IDS="${PHASE1_55H_VIDEO_IDS:-037,100,116,120,158,160,210}"
RSS_GUARD_MB="${RSS_GUARD_MB:-9000}"

mkdir -p "$OUT_DIR"

if [[ -f "$OUT_DIR/session_k1_n7.jsonl" && -f "$OUT_DIR/baseline_k1_n7.jsonl" && -f "$OUT_DIR/summary_k1_n7.json" ]]; then
  echo "[1.55H] reusing existing run outputs in $OUT_DIR"
else
  if [[ -f "$OUT_DIR/session_k1_n7.jsonl" || -f "$OUT_DIR/baseline_k1_n7.jsonl" || -f "$OUT_DIR/summary_k1_n7.json" ]]; then
    echo "[1.55H] incomplete prior outputs detected in $OUT_DIR; rerunning and overwriting partial artifacts"
  fi
  "$PY" scripts/run_kv_selective_reprefill_v2.py \
    --mode both \
    --video-ids "$VIDEO_IDS" \
    --frame-count 32 \
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
  --label phase1_55H_k1_32f_short_probe
