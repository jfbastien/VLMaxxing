#!/usr/bin/env bash
# Phase 1.63G — Gemma Track B sparse-ViT architecture check.
#
# Runs dense Gemma vision execution against compact post-layer L=2/kr=0.50
# Gemma vision execution on the same VideoMME n=60 manifest used by Qwen 1.63.
# Scope is intentionally vision-tower-only: the compact sequence is scattered
# back before the language model sees it, so LM prefill/decode remain dense.

set -euo pipefail

cd "$(dirname "$0")/.."

PY="${PYTHON:-./.venv/bin/python}"
MODEL_PATH="${PHASE1_63G_MODEL_PATH:-$HOME/models/gemma-4-e4b-it-4bit}"
MANIFEST="${PHASE1_63G_MANIFEST:-research/benchmark_manifests/videomme_combined_v1_n60.toml}"
OUT_DIR="${PHASE1_63G_OUT_DIR:-research/experiments/2026/artifacts/phase1_63G_gemma_track_b}"
RSS_GUARD_MB="${RSS_GUARD_MB:-9000}"
FRAME_COUNT="${PHASE1_63G_FRAME_COUNT:-8}"
EXPECTED_ITEMS="${PHASE1_63G_EXPECTED_ITEMS:-60}"

mkdir -p "$OUT_DIR"

DENSE_JSONL="$OUT_DIR/dense_${FRAME_COUNT}f.jsonl"
DENSE_SUMMARY="$OUT_DIR/dense_${FRAME_COUNT}f_summary.json"
SPARSE_JSONL="$OUT_DIR/sparse_L2_kr050_${FRAME_COUNT}f.jsonl"
SPARSE_SUMMARY="$OUT_DIR/sparse_L2_kr050_${FRAME_COUNT}f_summary.json"
PAIR_SUMMARY="$OUT_DIR/pair_summary.json"
PAIRED_ITEMS="$OUT_DIR/paired_items.jsonl"

if [[ -f "$DENSE_JSONL" && -f "$DENSE_SUMMARY" ]]; then
  echo "[1.63G] reusing dense Gemma arm in $OUT_DIR"
else
  if [[ -f "$DENSE_JSONL" || -f "$DENSE_SUMMARY" ]]; then
    echo "[1.63G] incomplete dense outputs detected; rerunning"
  fi
  "$PY" scripts/run_phase1_63G_gemma_track_b.py \
    --manifest "$MANIFEST" \
    --frame-count "$FRAME_COUNT" \
    --max-tokens 32 \
    --vision-tower-keep-rate 1.0 \
    --model-path "$MODEL_PATH" \
    --rss-guard-mb "$RSS_GUARD_MB" \
    --output "$DENSE_JSONL" \
    --summary "$DENSE_SUMMARY" \
    --allow-dirty
fi

if [[ -f "$SPARSE_JSONL" && -f "$SPARSE_SUMMARY" ]]; then
  echo "[1.63G] reusing sparse Gemma arm in $OUT_DIR"
else
  if [[ -f "$SPARSE_JSONL" || -f "$SPARSE_SUMMARY" ]]; then
    echo "[1.63G] incomplete sparse outputs detected; rerunning"
  fi
  "$PY" scripts/run_phase1_63G_gemma_track_b.py \
    --manifest "$MANIFEST" \
    --frame-count "$FRAME_COUNT" \
    --max-tokens 32 \
    --vision-tower-layer 2 \
    --vision-tower-keep-rate 0.50 \
    --model-path "$MODEL_PATH" \
    --rss-guard-mb "$RSS_GUARD_MB" \
    --output "$SPARSE_JSONL" \
    --summary "$SPARSE_SUMMARY" \
    --allow-dirty
fi

"$PY" scripts/analyze_phase1_63_track_b_sparse.py \
  --dense-jsonl "$DENSE_JSONL" \
  --sparse-jsonl "$SPARSE_JSONL" \
  --dense-summary "$DENSE_SUMMARY" \
  --sparse-summary "$SPARSE_SUMMARY" \
  --output "$PAIR_SUMMARY" \
  --paired-items "$PAIRED_ITEMS" \
  --expected-items "$EXPECTED_ITEMS" \
  --sparse-execution-scope "Gemma compact post-layer vision execution: dense patch embed and early vision blocks through L, compact execution for remaining vision blocks, scatter before pooler/merger so LLM prompt geometry is unchanged."
