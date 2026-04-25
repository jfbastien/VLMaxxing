#!/usr/bin/env bash
# Phase 1.55F-medium — adaptive Q3 post-Q2 state on the medium bucket.
#
# Why this exists:
# - 1.55F short showed the strongest C-PERSIST result in the repo:
#   Q1 cold, Q2 K=1, Q3 K=0 from the repaired Q2 state.
# - 1.55G showed the fixed K=1 policy survives the same medium tranche cleanly.
# - This is the direct scope test of whether the adaptive repair generalizes
#   beyond short clips.
#
# Runtime estimate on the fixed 10-clip medium tranche:
# - session + baseline: ~60-75 min
# - paired analysis: <1 min

set -euo pipefail

cd "$(dirname "$0")/.."

PY="${PYTHON:-./.venv/bin/python}"
MODEL_PATH="${PHASE1_55F_MEDIUM_MODEL_PATH:-$HOME/models/Qwen2.5-VL-7B-Instruct-4bit}"
OUT_DIR="${PHASE1_55F_MEDIUM_OUT_DIR:-research/experiments/2026/artifacts/phase1_55F_medium_adaptive_replication}"
VIDEO_IDS="${PHASE1_55F_MEDIUM_VIDEO_IDS:-320,354,364,380,407,408,426,484,486,531}"
RSS_GUARD_MB="${RSS_GUARD_MB:-9000}"

mkdir -p "$OUT_DIR"

if [[ -f "$OUT_DIR/session_k1_n10.jsonl" && -f "$OUT_DIR/baseline_k1_n10.jsonl" && -f "$OUT_DIR/summary_k1_n10.json" ]]; then
  echo "[1.55F-medium] reusing existing run outputs in $OUT_DIR"
else
  if [[ -f "$OUT_DIR/session_k1_n10.jsonl" || -f "$OUT_DIR/baseline_k1_n10.jsonl" || -f "$OUT_DIR/summary_k1_n10.json" ]]; then
    echo "[1.55F-medium] incomplete prior outputs detected in $OUT_DIR; rerunning and overwriting partial artifacts"
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
  --session-jsonl "$OUT_DIR/session_k1_n10.jsonl" \
  --baseline-jsonl "$OUT_DIR/baseline_k1_n10.jsonl" \
  --output "$OUT_DIR/pair_metrics_k1_n10.json" \
  --paired-queries "$OUT_DIR/paired_queries_k1_n10.jsonl" \
  --label phase1_55F_medium_adaptive_replication
