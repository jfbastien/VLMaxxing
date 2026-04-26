#!/usr/bin/env bash
# Phase 1.63 — Track B compact Qwen ViT execution.
#
# This is the minimal real skipped-work Track B MVP. It reuses the already
# validated 1.51V Qwen compact vision execution path and pairs dense vs
# L=2/kr=0.50 sparse arms on the same VideoMME combined n=60 manifest.

set -euo pipefail

cd "$(dirname "$0")/.."

PY="${PYTHON:-./.venv/bin/python}"
MODEL_PATH="${PHASE1_63_MODEL_PATH:-$HOME/models/Qwen2.5-VL-7B-Instruct-4bit}"
MANIFEST="${PHASE1_63_MANIFEST:-research/benchmark_manifests/videomme_combined_v1_n60.toml}"
OUT_DIR="${PHASE1_63_OUT_DIR:-research/experiments/2026/artifacts/phase1_63_track_b_sparse_vit}"
RSS_GUARD_MB="${RSS_GUARD_MB:-9000}"

mkdir -p "$OUT_DIR"

if [[ -f "$OUT_DIR/dense_8f.jsonl" && -f "$OUT_DIR/dense_8f_summary.json" ]]; then
  echo "[1.63] reusing dense arm in $OUT_DIR"
else
  if [[ -f "$OUT_DIR/dense_8f.jsonl" || -f "$OUT_DIR/dense_8f_summary.json" ]]; then
    echo "[1.63] incomplete dense outputs detected; rerunning and overwriting partial artifacts"
  fi
  "$PY" scripts/run_phase1_51V.py \
    --manifest "$MANIFEST" \
    --frame-count 8 \
    --max-tokens 32 \
    --vision-tower-keep-rate 1.0 \
    --model-path "$MODEL_PATH" \
    --rss-guard-mb "$RSS_GUARD_MB" \
    --output "$OUT_DIR/dense_8f.jsonl" \
    --summary "$OUT_DIR/dense_8f_summary.json" \
    --allow-dirty
fi

if [[ -f "$OUT_DIR/sparse_L2_kr050_8f.jsonl" && -f "$OUT_DIR/sparse_L2_kr050_8f_summary.json" ]]; then
  echo "[1.63] reusing sparse arm in $OUT_DIR"
else
  if [[ -f "$OUT_DIR/sparse_L2_kr050_8f.jsonl" || -f "$OUT_DIR/sparse_L2_kr050_8f_summary.json" ]]; then
    echo "[1.63] incomplete sparse outputs detected; rerunning and overwriting partial artifacts"
  fi
  "$PY" scripts/run_phase1_51V.py \
    --manifest "$MANIFEST" \
    --frame-count 8 \
    --max-tokens 32 \
    --vision-tower-layer 2 \
    --vision-tower-keep-rate 0.50 \
    --model-path "$MODEL_PATH" \
    --rss-guard-mb "$RSS_GUARD_MB" \
    --output "$OUT_DIR/sparse_L2_kr050_8f.jsonl" \
    --summary "$OUT_DIR/sparse_L2_kr050_8f_summary.json" \
    --allow-dirty
fi

"$PY" scripts/analyze_phase1_63_track_b_sparse.py \
  --dense-jsonl "$OUT_DIR/dense_8f.jsonl" \
  --sparse-jsonl "$OUT_DIR/sparse_L2_kr050_8f.jsonl" \
  --dense-summary "$OUT_DIR/dense_8f_summary.json" \
  --sparse-summary "$OUT_DIR/sparse_L2_kr050_8f_summary.json" \
  --output "$OUT_DIR/pair_summary.json" \
  --paired-items "$OUT_DIR/paired_items.jsonl"
