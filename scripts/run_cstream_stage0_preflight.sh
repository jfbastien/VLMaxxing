#!/usr/bin/env bash
# C-STREAM Stage 0 preflight.
#
# Runs the current Qwen session-streaming candidate on a tiny VideoMME slice and
# hard-fails unless it is mechanically healthy enough to justify Stage 1. This
# is a stop/go preflight, not paper headline evidence.

set -euo pipefail

cd "$(dirname "$0")/.."

PY="${PYTHON:-./.venv/bin/python}"
OUT_DIR="${CSTREAM_STAGE0_OUT_DIR:-research/experiments/2026/artifacts/cstream_stage0_preflight}"
MANIFEST="${CSTREAM_STAGE0_MANIFEST:-research/benchmark_manifests/videomme_dev_v1.toml}"
MODEL_PATH="${CSTREAM_STAGE0_MODEL_PATH:-$HOME/models/Qwen2.5-VL-7B-Instruct-4bit}"
N_SEEDS="${CSTREAM_STAGE0_N_SEEDS:-2}"
FRAME_COUNT="${CSTREAM_STAGE0_FRAME_COUNT:-8}"
MAX_TOKENS="${CSTREAM_STAGE0_MAX_TOKENS:-32}"
RSS_GUARD_MB="${CSTREAM_STAGE0_RSS_GUARD_MB:-10000}"
FORCE="${CSTREAM_STAGE0_FORCE:-0}"

mkdir -p "$OUT_DIR"

COLD_JSONL="$OUT_DIR/cold.jsonl"
COLD_SUMMARY="$OUT_DIR/cold_summary.json"
STREAM_JSONL="$OUT_DIR/streaming.jsonl"
STREAM_SUMMARY="$OUT_DIR/streaming_summary.json"
PAIR_SUMMARY="$OUT_DIR/pair_summary.json"
PAIRED_QUERIES="$OUT_DIR/paired_queries.jsonl"
PER_CLIP="$OUT_DIR/per_clip_bucket_tally.json"
STAGE_SUMMARY="$OUT_DIR/stage0_summary.json"

if [[ "$FORCE" != "1" && -f "$STAGE_SUMMARY" ]]; then
  if "$PY" scripts/validate_cstream_stage0_preflight.py \
    --pair-summary "$PAIR_SUMMARY" \
    --cold-summary "$COLD_SUMMARY" \
    --streaming-summary "$STREAM_SUMMARY" \
    --output "$STAGE_SUMMARY"; then
    echo "[cstream-stage0] reusing passing preflight in $OUT_DIR"
    exit 0
  fi
  echo "[cstream-stage0] existing preflight did not pass; rerunning"
fi

"$PY" scripts/run_phase1_30_scaleout_streaming.py \
  --stack cold \
  --manifest "$MANIFEST" \
  --frame-count "$FRAME_COUNT" \
  --max-tokens "$MAX_TOKENS" \
  --model-path "$MODEL_PATH" \
  --n-seeds "$N_SEEDS" \
  --rss-guard-mb "$RSS_GUARD_MB" \
  --allow-dirty \
  --output "$COLD_JSONL" \
  --summary "$COLD_SUMMARY"

"$PY" scripts/run_phase1_30_scaleout_streaming.py \
  --stack streaming \
  --manifest "$MANIFEST" \
  --frame-count "$FRAME_COUNT" \
  --max-tokens "$MAX_TOKENS" \
  --model-path "$MODEL_PATH" \
  --n-seeds "$N_SEEDS" \
  --rss-guard-mb "$RSS_GUARD_MB" \
  --vision-tower-keep-rate 1.0 \
  --allow-dirty \
  --output "$STREAM_JSONL" \
  --summary "$STREAM_SUMMARY"

"$PY" scripts/analyze_phase1_30_scaleout_streaming_pair.py \
  --cold-jsonl "$COLD_JSONL" \
  --streaming-jsonl "$STREAM_JSONL" \
  --cold-summary "$COLD_SUMMARY" \
  --streaming-summary "$STREAM_SUMMARY" \
  --pair-summary "$PAIR_SUMMARY" \
  --per-clip-buckets "$PER_CLIP" \
  --paired-queries "$PAIRED_QUERIES"

"$PY" scripts/validate_cstream_stage0_preflight.py \
  --pair-summary "$PAIR_SUMMARY" \
  --cold-summary "$COLD_SUMMARY" \
  --streaming-summary "$STREAM_SUMMARY" \
  --output "$STAGE_SUMMARY"

echo "[cstream-stage0] wrote $STAGE_SUMMARY"
