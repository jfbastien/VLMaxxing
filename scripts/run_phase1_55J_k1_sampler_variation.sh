#!/usr/bin/env bash
# Phase 1.55J — K=1 short-bucket sampler-variation scout.
#
# Tests whether the fixed K=1 "no observed paired drift" cell is conditioned on
# greedy decoding by rerunning the 1.55D short tranche with deterministic
# temperature sampling.

set -euo pipefail

cd "$(dirname "$0")/.."

PY="${PYTHON:-./.venv/bin/python}"
MODEL_PATH="${MODEL_PATH:-$HOME/models/Qwen2.5-VL-7B-Instruct-4bit}"
RSS_GUARD_MB="${RSS_GUARD_MB:-9000}"
OUT_DIR="${1:-research/experiments/2026/artifacts/phase1_55J_k1_sampler_variation}"

mkdir -p "$OUT_DIR"

if [[ -f "$OUT_DIR/session_k1_n7.jsonl" && -f "$OUT_DIR/baseline_k1_n7.jsonl" && -f "$OUT_DIR/summary_k1_n7.json" ]]; then
  echo "[1.55J] reusing existing run outputs in $OUT_DIR"
else
  if [[ -f "$OUT_DIR/session_k1_n7.jsonl" || -f "$OUT_DIR/baseline_k1_n7.jsonl" || -f "$OUT_DIR/summary_k1_n7.json" ]]; then
    echo "[1.55J] incomplete prior outputs detected in $OUT_DIR; rerunning and overwriting partial artifacts"
  fi
  "$PY" scripts/run_kv_selective_reprefill_v2.py \
    --reprefill-k 1 \
    --frame-count 20 \
    --temperature 0.1 \
    --top-p 0.95 \
    --min-p 0.0 \
    --model-path "$MODEL_PATH" \
    --rss-guard-mb "$RSS_GUARD_MB" \
    --output-dir "$OUT_DIR"
fi

"$PY" scripts/analyze_selective_reprefill_pairs.py \
  --session-jsonl "$OUT_DIR/session_k1_n7.jsonl" \
  --baseline-jsonl "$OUT_DIR/baseline_k1_n7.jsonl" \
  --pair-metrics "$OUT_DIR/pair_metrics_k1_n7.json" \
  --paired-queries "$OUT_DIR/paired_queries_k1_n7.jsonl"
