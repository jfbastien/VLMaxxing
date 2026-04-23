#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

PY="${PYTHON:-./.venv/bin/python}"
OUT_DIR="research/experiments/2026/artifacts/phase1_30_sam_streaming"
DEV_MANIFEST="research/benchmark_manifests/videomme_dev_v1.toml"
HOLDOUT_MANIFEST="research/benchmark_manifests/videomme_holdout_v1.toml"
MODEL_PATH="${PHASE1_30_MODEL_PATH:-$HOME/models/Qwen2.5-VL-7B-Instruct-4bit}"
RSS_GUARD_MB="${PHASE1_30_RSS_GUARD_MB:-10000}"
N_SEEDS="${PHASE1_30_N_SEEDS:-0}"
VISION_TOWER_LAYER="${PHASE1_30_VISION_TOWER_LAYER:-2}"
VISION_TOWER_KEEP_RATE="${PHASE1_30_VISION_TOWER_KEEP_RATE:-0.50}"
DRIFT_REFRESH_POLICY="${PHASE1_30_DRIFT_REFRESH_POLICY:-off}"

mkdir -p "$OUT_DIR"

"$PY" scripts/run_phase1_30_sam_streaming.py \
  --stack cold \
  --manifest "$DEV_MANIFEST" \
  --manifest "$HOLDOUT_MANIFEST" \
  --frame-count 8 \
  --max-tokens 32 \
  --model-path "$MODEL_PATH" \
  --n-seeds "$N_SEEDS" \
  --rss-guard-mb "$RSS_GUARD_MB" \
  --drift-refresh-policy "$DRIFT_REFRESH_POLICY" \
  --allow-dirty \
  --output "$OUT_DIR/cold.jsonl" \
  --summary "$OUT_DIR/cold_summary.json"

"$PY" scripts/run_phase1_30_sam_streaming.py \
  --stack streaming \
  --manifest "$DEV_MANIFEST" \
  --manifest "$HOLDOUT_MANIFEST" \
  --frame-count 8 \
  --max-tokens 32 \
  --model-path "$MODEL_PATH" \
  --n-seeds "$N_SEEDS" \
  --rss-guard-mb "$RSS_GUARD_MB" \
  --vision-tower-layer "$VISION_TOWER_LAYER" \
  --vision-tower-keep-rate "$VISION_TOWER_KEEP_RATE" \
  --drift-refresh-policy "$DRIFT_REFRESH_POLICY" \
  --allow-dirty \
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
