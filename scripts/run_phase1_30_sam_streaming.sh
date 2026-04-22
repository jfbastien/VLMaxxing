#!/usr/bin/env bash
set -euo pipefail

PY="${PYTHON:-./.venv/bin/python}"
OUT_DIR="research/experiments/2026/artifacts/phase1_30_sam_streaming"
DEV_MANIFEST="research/benchmark_manifests/videomme_dev_v1.toml"
HOLDOUT_MANIFEST="research/benchmark_manifests/videomme_holdout_v1.toml"

mkdir -p "$OUT_DIR"

"$PY" scripts/run_phase1_30_sam_streaming.py \
  --stack cold \
  --manifest "$DEV_MANIFEST" \
  --manifest "$HOLDOUT_MANIFEST" \
  --frame-count 8 \
  --max-tokens 32 \
  --output "$OUT_DIR/cold.jsonl" \
  --summary "$OUT_DIR/cold_summary.json"

"$PY" scripts/run_phase1_30_sam_streaming.py \
  --stack streaming \
  --manifest "$DEV_MANIFEST" \
  --manifest "$HOLDOUT_MANIFEST" \
  --frame-count 8 \
  --max-tokens 32 \
  --vision-tower-layer 2 \
  --vision-tower-keep-rate 0.50 \
  --output "$OUT_DIR/streaming.jsonl" \
  --summary "$OUT_DIR/streaming_summary.json"

"$PY" scripts/analyze_phase1_30_sam_streaming_pair.py \
  --cold-jsonl "$OUT_DIR/cold.jsonl" \
  --streaming-jsonl "$OUT_DIR/streaming.jsonl" \
  --cold-summary "$OUT_DIR/cold_summary.json" \
  --streaming-summary "$OUT_DIR/streaming_summary.json" \
  --pair-summary "$OUT_DIR/pair_summary.json" \
  --per-clip-buckets "$OUT_DIR/per_clip_bucket_tally.json" \
  --paired-queries "$OUT_DIR/paired_queries.jsonl"
