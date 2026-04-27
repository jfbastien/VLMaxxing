#!/usr/bin/env bash
# Phase 1.63E — Track B Qwen sparse-ViT frame-budget scaling.
#
# Runs the same dense vs compact post-layer L=2/kr=0.50 Qwen Track B protocol
# as 1.63 at 16f, 20f, and 32f. The landed 8f 1.63 cell can be included in
# the summary automatically when present, but this wrapper only computes the
# three additional frame-budget cells.

set -euo pipefail

cd "$(dirname "$0")/.."

PY="${PYTHON:-./.venv/bin/python}"
MODEL_PATH="${PHASE1_63E_MODEL_PATH:-$HOME/models/Qwen2.5-VL-7B-Instruct-4bit}"
MANIFEST="${PHASE1_63E_MANIFEST:-research/benchmark_manifests/videomme_combined_v1_n60.toml}"
OUT_DIR="${PHASE1_63E_OUT_DIR:-research/experiments/2026/artifacts/phase1_63E_track_b_frame_scaling}"
REFERENCE_8F="${PHASE1_63E_REFERENCE_8F:-research/experiments/2026/artifacts/phase1_63_track_b_sparse_vit/pair_summary.json}"
RSS_GUARD_MB="${RSS_GUARD_MB:-9000}"
FRAME_COUNTS="${PHASE1_63E_FRAME_COUNTS:-16 20 32}"

mkdir -p "$OUT_DIR"

SUMMARY_ARGS=()
REFERENCE_ARGS=()
if [[ " $FRAME_COUNTS " != *" 8 "* && -f "$REFERENCE_8F" ]]; then
  SUMMARY_ARGS+=(--cell 8 "$REFERENCE_8F")
  REFERENCE_ARGS+=(--reference-frame-count 8)
fi

for FRAME_COUNT in $FRAME_COUNTS; do
  DENSE_JSONL="$OUT_DIR/dense_${FRAME_COUNT}f.jsonl"
  DENSE_SUMMARY="$OUT_DIR/dense_${FRAME_COUNT}f_summary.json"
  SPARSE_JSONL="$OUT_DIR/sparse_L2_kr050_${FRAME_COUNT}f.jsonl"
  SPARSE_SUMMARY="$OUT_DIR/sparse_L2_kr050_${FRAME_COUNT}f_summary.json"
  PAIR_SUMMARY="$OUT_DIR/pair_summary_${FRAME_COUNT}f.json"
  PAIRED_ITEMS="$OUT_DIR/paired_items_${FRAME_COUNT}f.jsonl"

  if [[ -f "$DENSE_JSONL" && -f "$DENSE_SUMMARY" ]]; then
    echo "[1.63E] reusing dense ${FRAME_COUNT}f arm in $OUT_DIR"
  else
    if [[ -f "$DENSE_JSONL" || -f "$DENSE_SUMMARY" ]]; then
      echo "[1.63E] incomplete dense ${FRAME_COUNT}f outputs detected; rerunning"
    fi
    "$PY" scripts/run_phase1_51V.py \
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
    echo "[1.63E] reusing sparse ${FRAME_COUNT}f arm in $OUT_DIR"
  else
    if [[ -f "$SPARSE_JSONL" || -f "$SPARSE_SUMMARY" ]]; then
      echo "[1.63E] incomplete sparse ${FRAME_COUNT}f outputs detected; rerunning"
    fi
    "$PY" scripts/run_phase1_51V.py \
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
    --expected-items 60

  SUMMARY_ARGS+=(--cell "$FRAME_COUNT" "$PAIR_SUMMARY")
done

"$PY" scripts/summarize_phase1_63_track_b_scaling.py \
  "${SUMMARY_ARGS[@]}" \
  "${REFERENCE_ARGS[@]}" \
  --output "$OUT_DIR/scaling_summary.json"
