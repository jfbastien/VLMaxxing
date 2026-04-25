#!/usr/bin/env bash
# Phase 1.55G — K=1 selective re-prefill medium-bucket replication.
#
# Why this exists:
# - 1.55D K=1 is currently strong but short-bucket-only.
# - This is the cheapest direct test of whether the no-observed-drift result is
#   regime-specific or a broader property of the repaired Qwen 20f path.
#
# Runtime estimate on the 10-clip medium tranche:
# - session + baseline: ~100-130 min
# - paired analysis: <1 min

set -euo pipefail

cd "$(dirname "$0")/.."

PY="${PYTHON:-./.venv/bin/python}"
MODEL_PATH="${PHASE1_55G_MODEL_PATH:-$HOME/models/Qwen2.5-VL-7B-Instruct-4bit}"
OUT_DIR="${PHASE1_55G_OUT_DIR:-research/experiments/2026/artifacts/phase1_55G_k1_medium_replication}"
VIDEO_IDS="${PHASE1_55G_VIDEO_IDS:-320,354,364,380,407,408,426,484,486,531}"

mkdir -p "$OUT_DIR"

if [[ -f "$OUT_DIR/session_k1_n10.jsonl" && -f "$OUT_DIR/baseline_k1_n10.jsonl" && -f "$OUT_DIR/summary_k1_n10.json" ]]; then
  echo "[1.55G] reusing existing run outputs in $OUT_DIR"
else
  "$PY" scripts/run_kv_selective_reprefill_v2.py \
    --mode both \
    --video-ids "$VIDEO_IDS" \
    --frame-count 20 \
    --max-tokens 32 \
    --reprefill-k 1 \
    --model-path "$MODEL_PATH" \
    --output-dir "$OUT_DIR"
fi

"$PY" scripts/analyze_selective_reprefill_pairs.py \
  --session-jsonl "$OUT_DIR/session_k1_n10.jsonl" \
  --baseline-jsonl "$OUT_DIR/baseline_k1_n10.jsonl" \
  --output "$OUT_DIR/pair_metrics_k1_n10.json" \
  --label phase1_55G_k1_medium_replication
