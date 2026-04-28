#!/usr/bin/env bash
# Phase 1.63H — 16-frame Qwen Track B keep-rate sweep.
#
# Bracket the safe operating point at 16f after 1.63E showed kr=0.50 catastrophically
# breaks instruction-following (22/60 parse failures, accuracy 0.217 vs dense 0.633).
# This script reuses the dense_16f.jsonl already produced and committed by 1.63E
# and runs sparse Qwen 16f at three less-aggressive keep-rates.
#
# Resume-safe: any kr cell whose sparse JSONL + summary already exist is skipped.

set -euo pipefail

cd "$(dirname "$0")/.."

PY="${PYTHON:-./.venv/bin/python}"
MODEL_PATH="${PHASE1_63H_MODEL_PATH:-$HOME/models/Qwen2.5-VL-7B-Instruct-4bit}"
MANIFEST="${PHASE1_63H_MANIFEST:-research/benchmark_manifests/videomme_combined_v1_n60.toml}"
OUT_DIR="${PHASE1_63H_OUT_DIR:-research/experiments/2026/artifacts/phase1_63H_16f_kr_sweep}"
DENSE_REFERENCE_DIR="${PHASE1_63H_DENSE_REFERENCE_DIR:-research/experiments/2026/artifacts/phase1_63E_track_b_frame_scaling}"
RSS_GUARD_MB="${RSS_GUARD_MB:-9000}"
KEEP_RATES="${PHASE1_63H_KEEP_RATES:-0.65 0.75 0.85}"
LAYER="${PHASE1_63H_LAYER:-2}"

mkdir -p "$OUT_DIR"

DENSE_JSONL="$DENSE_REFERENCE_DIR/dense_16f.jsonl"
DENSE_SUMMARY="$DENSE_REFERENCE_DIR/dense_16f_summary.json"

if [[ ! -f "$DENSE_JSONL" || ! -f "$DENSE_SUMMARY" ]]; then
  echo "[1.63H] missing dense 16f reference; expected at $DENSE_JSONL" >&2
  exit 2
fi

echo "[1.63H] reusing dense 16f reference from $DENSE_REFERENCE_DIR"

SUMMARY_ARGS=(--cell 50 "$DENSE_REFERENCE_DIR/pair_summary_16f.json")

for KR in $KEEP_RATES; do
  KR_TAG="$(printf %s "$KR" | tr -d '.' | sed 's/^0*//; s/^$/0/')"
  KR_TAG="kr0${KR_TAG}"
  SPARSE_JSONL="$OUT_DIR/sparse_L${LAYER}_${KR_TAG}_16f.jsonl"
  SPARSE_SUMMARY="$OUT_DIR/sparse_L${LAYER}_${KR_TAG}_16f_summary.json"
  PAIR_SUMMARY="$OUT_DIR/pair_summary_${KR_TAG}_16f.json"
  PAIRED_ITEMS="$OUT_DIR/paired_items_${KR_TAG}_16f.jsonl"

  if [[ -f "$SPARSE_JSONL" && -f "$SPARSE_SUMMARY" ]]; then
    echo "[1.63H] reusing sparse arm L=${LAYER} kr=${KR} in $OUT_DIR"
  else
    if [[ -f "$SPARSE_JSONL" || -f "$SPARSE_SUMMARY" ]]; then
      echo "[1.63H] incomplete sparse outputs for kr=${KR} detected; rerunning"
    fi
    "$PY" scripts/run_phase1_51V.py \
      --manifest "$MANIFEST" \
      --frame-count 16 \
      --max-tokens 32 \
      --vision-tower-layer "$LAYER" \
      --vision-tower-keep-rate "$KR" \
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

  KR_PERCENT=$(python3 -c "print(int(round(float('$KR') * 100)))")
  SUMMARY_ARGS+=(--cell "$KR_PERCENT" "$PAIR_SUMMARY")
done

echo "[1.63H] sweep complete; per-kr pair summaries written to $OUT_DIR"
