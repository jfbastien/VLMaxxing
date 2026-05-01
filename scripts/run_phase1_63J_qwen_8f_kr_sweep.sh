#!/usr/bin/env bash
# Phase 1.63J — Qwen 8f C-CEILING timing sweep at kr=0.25/0.75.
#
# Reuses the dense 8f reference and kr=0.50 pair summary from 1.63E.
# This is timing/arithmetic validation with fidelity reported separately; do
# not cite it as a fidelity-clean Qwen kr curve unless the summaries say so.

set -euo pipefail

cd "$(dirname "$0")/.."

PY="${PYTHON:-./.venv/bin/python}"
MODEL_PATH="${PHASE1_63J_MODEL_PATH:-$HOME/models/Qwen2.5-VL-7B-Instruct-4bit}"
MANIFEST="${PHASE1_63J_MANIFEST:-research/benchmark_manifests/videomme_combined_v1_n60.toml}"
OUT_DIR="${PHASE1_63J_OUT_DIR:-research/experiments/2026/artifacts/phase1_63J_qwen_8f_kr_sweep}"
DENSE_REFERENCE_DIR="${PHASE1_63J_DENSE_REFERENCE_DIR:-research/experiments/2026/artifacts/phase1_63E_track_b_frame_scaling}"
RSS_GUARD_MB="${RSS_GUARD_MB:-9000}"
KEEP_RATES="${PHASE1_63J_KEEP_RATES:-0.75 0.25}"
LAYER="${PHASE1_63J_LAYER:-2}"

mkdir -p "$OUT_DIR"

DENSE_JSONL="$DENSE_REFERENCE_DIR/dense_8f.jsonl"
DENSE_SUMMARY="$DENSE_REFERENCE_DIR/dense_8f_summary.json"
REFERENCE_KR050="$DENSE_REFERENCE_DIR/pair_summary_8f.json"

if [[ ! -f "$DENSE_JSONL" || ! -f "$DENSE_SUMMARY" || ! -f "$REFERENCE_KR050" ]]; then
  echo "[1.63J] missing 1.63E dense/kr=0.50 reference in $DENSE_REFERENCE_DIR" >&2
  exit 2
fi

SUMMARY_ARGS=(--cell 0.50 "$REFERENCE_KR050")

for KR in $KEEP_RATES; do
  KR_TAG="$(printf %s "$KR" | tr -d '.' | sed 's/^0*//; s/^$/0/')"
  KR_TAG="kr0${KR_TAG}"
  SPARSE_JSONL="$OUT_DIR/sparse_L${LAYER}_${KR_TAG}_8f.jsonl"
  SPARSE_SUMMARY="$OUT_DIR/sparse_L${LAYER}_${KR_TAG}_8f_summary.json"
  PAIR_SUMMARY="$OUT_DIR/pair_summary_${KR_TAG}_8f.json"
  PAIRED_ITEMS="$OUT_DIR/paired_items_${KR_TAG}_8f.jsonl"

  if [[ -f "$SPARSE_JSONL" && -f "$SPARSE_SUMMARY" ]]; then
    echo "[1.63J] reusing sparse arm L=${LAYER} kr=${KR} in $OUT_DIR"
  else
    if [[ -f "$SPARSE_JSONL" || -f "$SPARSE_SUMMARY" ]]; then
      echo "[1.63J] incomplete sparse outputs for kr=${KR} detected; rerunning"
    fi
    "$PY" scripts/run_phase1_51V.py \
      --manifest "$MANIFEST" \
      --frame-count 8 \
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

  SUMMARY_ARGS+=(--cell "$KR" "$PAIR_SUMMARY")
done

"$PY" scripts/summarize_phase1_63i_kr_bracket.py \
  --phase 1.63J \
  "${SUMMARY_ARGS[@]}" \
  --output "$OUT_DIR/kr_sweep_summary.json"

echo "[1.63J] wrote $OUT_DIR/kr_sweep_summary.json"
