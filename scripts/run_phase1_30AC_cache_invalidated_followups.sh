#!/usr/bin/env bash
# Phase 1.30AC — cache-invalidated follow-up pruning.
#
# Why this exists:
# - 1.30Z and 1.30AB proved that the current 1.30 family is not a follow-up
#   pruning result: every follow-up image token was cache-served.
# - 1.30AC is the first run that forces the follow-up vision tower to fire so
#   we can measure whether active follow-up pruning helps, hurts, or simply
#   costs too much under matched budgets.
#
# Runtime estimate with reused 1.30W cold control:
# - streaming full union: ~5-6 h
# - paired analysis: <1 min

set -euo pipefail

cd "$(dirname "$0")/.."

PY="${PYTHON:-./.venv/bin/python}"
MODEL_PATH="${MODEL_PATH:-$HOME/models/Qwen2.5-VL-7B-Instruct-4bit}"
RSS_GUARD_MB="${RSS_GUARD_MB:-9000}"
OUT="${1:-research/experiments/2026/artifacts/phase1_30AC_cache_invalidated_followups}"
REFERENCE_DIR="${REFERENCE_DIR:-research/experiments/2026/artifacts/phase1_30W_q0_dense_followup_pruned_full}"
RERUN_COLD="${PHASE1_30AC_RERUN_COLD:-0}"

mkdir -p "$OUT"

COLD_JSONL="$OUT/cold_dense.jsonl"
COLD_SUMMARY="$OUT/cold_dense_summary.json"

if [[ "$RERUN_COLD" != "1" && -f "$REFERENCE_DIR/cold_dense.jsonl" && -f "$REFERENCE_DIR/cold_dense_summary.json" ]]; then
  echo "[1.30AC] reusing 1.30W cold control from $REFERENCE_DIR"
  COLD_JSONL="$REFERENCE_DIR/cold_dense.jsonl"
  COLD_SUMMARY="$REFERENCE_DIR/cold_dense_summary.json"
elif [[ -f "$OUT/cold_dense.jsonl" && -f "$OUT/cold_dense_summary.json" ]]; then
  echo "[1.30AC] reusing cold arm in $OUT"
else
  "$PY" scripts/run_phase1_30_sam_streaming.py \
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

if [[ -f "$OUT/streaming_cache_invalidated_followups.jsonl" && -f "$OUT/streaming_cache_invalidated_followups_summary.json" ]]; then
  echo "[1.30AC] reusing existing streaming arm in $OUT"
else
  "$PY" scripts/run_phase1_30_sam_streaming.py \
    --allow-dirty \
    --stack streaming \
    --manifest research/benchmark_manifests/videomme_dev_v1.toml \
    --manifest research/benchmark_manifests/videomme_holdout_v1.toml \
    --frame-count 8 \
    --max-tokens 32 \
    --model-path "$MODEL_PATH" \
    --rss-guard-mb "$RSS_GUARD_MB" \
    --output "$OUT/streaming_cache_invalidated_followups.jsonl" \
    --summary "$OUT/streaming_cache_invalidated_followups_summary.json" \
    --vision-tower-layer 2 \
    --vision-tower-keep-rate 0.50 \
    --vision-tower-keep-rate-first-query 1.0 \
    --vision-tower-keep-rate-follow-ups 0.50 \
    --reset-cache-between-queries \
    --drift-refresh-policy off
fi

"$PY" scripts/analyze_phase1_30_sam_streaming_pair.py \
  --cold-jsonl "$COLD_JSONL" \
  --streaming-jsonl "$OUT/streaming_cache_invalidated_followups.jsonl" \
  --cold-summary "$COLD_SUMMARY" \
  --streaming-summary "$OUT/streaming_cache_invalidated_followups_summary.json" \
  --pair-summary "$OUT/pair_summary.json" \
  --per-clip-buckets "$OUT/per_clip_buckets.json" \
  --paired-queries "$OUT/paired_queries.jsonl"
