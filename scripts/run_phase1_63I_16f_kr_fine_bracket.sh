#!/usr/bin/env bash
# Phase 1.63I — Qwen 16f Track B keep-rate fine bracket.
#
# Tests whether a point between the 1.63H kr=0.75 near-miss and kr=0.85
# fidelity-safe/low-gain point can satisfy both fidelity and >=25% vision
# reduction. A negative result confirms the low-gain safe envelope.

set -euo pipefail

cd "$(dirname "$0")/.."

PY="${PYTHON:-./.venv/bin/python}"
MODEL_PATH="${PHASE1_63I_MODEL_PATH:-$HOME/models/Qwen2.5-VL-7B-Instruct-4bit}"
MANIFEST="${PHASE1_63I_MANIFEST:-research/benchmark_manifests/videomme_combined_v1_n60.toml}"
OUT_DIR="${PHASE1_63I_OUT_DIR:-research/experiments/2026/artifacts/phase1_63I_16f_kr_fine_bracket}"
DENSE_REFERENCE_DIR="${PHASE1_63I_DENSE_REFERENCE_DIR:-research/experiments/2026/artifacts/phase1_63E_track_b_frame_scaling}"
RSS_GUARD_MB="${RSS_GUARD_MB:-12000}"
KEEP_RATES="${PHASE1_63I_KEEP_RATES:-0.78 0.80 0.82}"
LAYER="${PHASE1_63I_LAYER:-2}"

mkdir -p "$OUT_DIR"

DENSE_JSONL="$DENSE_REFERENCE_DIR/dense_16f.jsonl"
DENSE_SUMMARY="$DENSE_REFERENCE_DIR/dense_16f_summary.json"
if [[ ! -f "$DENSE_JSONL" || ! -f "$DENSE_SUMMARY" ]]; then
  echo "[1.63I] missing dense 16f reference; expected $DENSE_JSONL and $DENSE_SUMMARY" >&2
  exit 2
fi

SUMMARY_ARGS=()
for KR in $KEEP_RATES; do
  KR_TAG="$(printf %s "$KR" | tr -d '.' | sed 's/^0*//; s/^$/0/')"
  KR_TAG="kr0${KR_TAG}"
  SPARSE_JSONL="$OUT_DIR/sparse_L${LAYER}_${KR_TAG}_16f.jsonl"
  SPARSE_SUMMARY="$OUT_DIR/sparse_L${LAYER}_${KR_TAG}_16f_summary.json"
  PAIR_SUMMARY="$OUT_DIR/pair_summary_${KR_TAG}_16f.json"
  PAIRED_ITEMS="$OUT_DIR/paired_items_${KR_TAG}_16f.jsonl"

  if [[ -f "$SPARSE_JSONL" && -f "$SPARSE_SUMMARY" ]]; then
    echo "[1.63I] reusing sparse arm L=${LAYER} kr=${KR} in $OUT_DIR"
  else
    if [[ -f "$SPARSE_JSONL" || -f "$SPARSE_SUMMARY" ]]; then
      echo "[1.63I] incomplete sparse outputs for kr=${KR} detected; rerunning"
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

  SUMMARY_ARGS+=(--cell "$KR" "$PAIR_SUMMARY")
done

"$PY" scripts/summarize_phase1_63i_kr_bracket.py \
  --phase 1.63I \
  "${SUMMARY_ARGS[@]}" \
  --output "$OUT_DIR/fine_bracket_summary.json"

echo "[1.63I] fine bracket complete; summary written to $OUT_DIR/fine_bracket_summary.json"
