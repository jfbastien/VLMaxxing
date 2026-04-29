#!/usr/bin/env bash
# Phase 1.62D — low-FPS dense VideoMME session baseline.
#
# This is the cheapest deployment-style baseline objection: do not cache or
# prune; just use fewer dense frames. It runs the same 57 VideoMME sessions /
# 171 queries as 1.30W, then pairs 4f and 2f cold-dense answers against the
# existing 8f cold-dense reference.

set -euo pipefail

cd "$(dirname "$0")/.."

PY="${PYTHON:-./.venv/bin/python}"
MODEL_PATH="${PHASE1_62D_MODEL_PATH:-$HOME/models/Qwen2.5-VL-7B-Instruct-4bit}"
OUT_DIR="${PHASE1_62D_OUT_DIR:-research/experiments/2026/artifacts/phase1_62D_lowfps_dense_videomme}"
REFERENCE_DIR="${PHASE1_62D_REFERENCE_DIR:-research/experiments/2026/artifacts/phase1_30W_q0_dense_followup_pruned_full}"
RSS_GUARD_MB="${RSS_GUARD_MB:-12000}"

mkdir -p "$OUT_DIR"

for FRAME_COUNT in 4 2; do
  JSONL="$OUT_DIR/cold_dense_${FRAME_COUNT}f.jsonl"
  SUMMARY="$OUT_DIR/cold_dense_${FRAME_COUNT}f_summary.json"
  if [[ -f "$JSONL" && -f "$SUMMARY" ]]; then
    echo "[1.62D] reusing existing ${FRAME_COUNT}f outputs in $OUT_DIR"
  else
    if [[ -f "$JSONL" || -f "$SUMMARY" ]]; then
      echo "[1.62D] incomplete prior ${FRAME_COUNT}f outputs detected; rerunning and overwriting partial artifacts"
    fi
    "$PY" scripts/run_phase1_30_scaleout_streaming.py \
      --stack cold \
      --manifest research/benchmark_manifests/videomme_dev_v1.toml \
      --manifest research/benchmark_manifests/videomme_holdout_v1.toml \
      --frame-count "$FRAME_COUNT" \
      --max-tokens 32 \
      --model-path "$MODEL_PATH" \
      --rss-guard-mb "$RSS_GUARD_MB" \
      --output "$JSONL" \
      --summary "$SUMMARY" \
      --allow-dirty
  fi

  "$PY" scripts/analyze_phase1_62_lowfps_dense.py \
    --reference-jsonl "$REFERENCE_DIR/cold_dense.jsonl" \
    --candidate-jsonl "$JSONL" \
    --output "$OUT_DIR/lowfps_${FRAME_COUNT}f_vs_8f_summary.json" \
    --paired-queries "$OUT_DIR/lowfps_${FRAME_COUNT}f_vs_8f_paired_queries.jsonl"
done

"$PY" scripts/summarize_phase1_62d_lowfps_dense.py \
  --cell 4 "$OUT_DIR/lowfps_4f_vs_8f_summary.json" \
  --cell 2 "$OUT_DIR/lowfps_2f_vs_8f_summary.json" \
  --output "$OUT_DIR/summary.json"
