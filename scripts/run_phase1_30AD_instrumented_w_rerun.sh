#!/usr/bin/env bash
# Phase 1.30AD — instrumented rerun of the landed 1.30W lane.
#
# Why this exists:
# - 1.30W is still the best landed 1.30 result, but it predates the image-token
#   instrumentation.
# - This rerun pins the published 1.30W number's mechanism so the paper can say
#   "Q0 admission + K-cache reuse" from a measurement, not from inference.
#
# Runtime estimate with reused 1.30W cold control:
# - streaming full union: ~1.5-2.5 h
# - paired analysis: <1 min

set -euo pipefail

cd "$(dirname "$0")/.."

PY="${PYTHON:-./.venv/bin/python}"
MODEL_PATH="${MODEL_PATH:-$HOME/models/Qwen2.5-VL-7B-Instruct-4bit}"
RSS_GUARD_MB="${RSS_GUARD_MB:-9000}"
OUT="${1:-research/experiments/2026/artifacts/phase1_30AD_instrumented_w_rerun}"
REFERENCE_DIR="${REFERENCE_DIR:-research/experiments/2026/artifacts/phase1_30W_q0_dense_followup_pruned_full}"
RERUN_COLD="${PHASE1_30AD_RERUN_COLD:-0}"

mkdir -p "$OUT"

COLD_JSONL="$OUT/cold_dense.jsonl"
COLD_SUMMARY="$OUT/cold_dense_summary.json"

if [[ "$RERUN_COLD" != "1" && -f "$REFERENCE_DIR/cold_dense.jsonl" && -f "$REFERENCE_DIR/cold_dense_summary.json" ]]; then
  echo "[1.30AD] reusing 1.30W cold control from $REFERENCE_DIR"
  COLD_JSONL="$REFERENCE_DIR/cold_dense.jsonl"
  COLD_SUMMARY="$REFERENCE_DIR/cold_dense_summary.json"
elif [[ -f "$OUT/cold_dense.jsonl" && -f "$OUT/cold_dense_summary.json" ]]; then
  echo "[1.30AD] reusing cold arm in $OUT"
else
  "$PY" scripts/run_phase1_30_scaleout_streaming.py \
    --allow-dirty \
    --stack cold \
    --manifest research/benchmark_manifests/videomme_dev_v1.toml \
    --manifest research/benchmark_manifests/videomme_holdout_v1.toml \
    --frame-count 8 \
    --max-tokens 32 \
    --model-path "$MODEL_PATH" \
    --rss-guard-mb "$RSS_GUARD_MB" \
    --output "$OUT/cold_dense.jsonl" \
    --summary "$OUT/cold_dense_summary.json" \
    --vision-tower-keep-rate 1.0 \
    --drift-refresh-policy off
fi

if [[ -f "$OUT/streaming_q0_dense_cache_reuse_followups.jsonl" && -f "$OUT/streaming_q0_dense_cache_reuse_followups_summary.json" ]]; then
  echo "[1.30AD] reusing existing streaming arm in $OUT"
else
  "$PY" scripts/run_phase1_30_scaleout_streaming.py \
    --allow-dirty \
    --stack streaming \
    --manifest research/benchmark_manifests/videomme_dev_v1.toml \
    --manifest research/benchmark_manifests/videomme_holdout_v1.toml \
    --frame-count 8 \
    --max-tokens 32 \
    --model-path "$MODEL_PATH" \
    --rss-guard-mb "$RSS_GUARD_MB" \
    --output "$OUT/streaming_q0_dense_cache_reuse_followups.jsonl" \
    --summary "$OUT/streaming_q0_dense_cache_reuse_followups_summary.json" \
    --vision-tower-layer 2 \
    --vision-tower-keep-rate 0.50 \
    --vision-tower-keep-rate-first-query 1.0 \
    --vision-tower-keep-rate-follow-ups 0.50 \
    --drift-refresh-policy off
fi

"$PY" scripts/analyze_phase1_30_scaleout_streaming_pair.py \
  --cold-jsonl "$COLD_JSONL" \
  --streaming-jsonl "$OUT/streaming_q0_dense_cache_reuse_followups.jsonl" \
  --cold-summary "$COLD_SUMMARY" \
  --streaming-summary "$OUT/streaming_q0_dense_cache_reuse_followups_summary.json" \
  --pair-summary "$OUT/pair_summary.json" \
  --per-clip-buckets "$OUT/per_clip_buckets.json" \
  --paired-queries "$OUT/paired_queries.jsonl"
