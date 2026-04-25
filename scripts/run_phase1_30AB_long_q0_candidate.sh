#!/usr/bin/env bash
# Phase 1.30AB — long-bucket Q0 keep-rate candidate.
#
# Why this exists:
# - 1.30Z falsified the aggressive kr_Q0=0.67 long-bucket candidate.
# - The next falsifiable question is where the long-Q0 keep-rate boundary lives
#   when follow-ups remain pure cache-reuse.
#
# Usage:
#   ./scripts/run_phase1_30AB_long_q0_candidate.sh 0.75
#   ./scripts/run_phase1_30AB_long_q0_candidate.sh 0.80 /tmp/outdir
#
# Runtime estimate with committed cold-control reuse:
# - streaming long bucket: ~25-45 min
# - paired analysis: <1 min

set -euo pipefail

cd "$(dirname "$0")/.."

RATE="${1:?usage: run_phase1_30AB_long_q0_candidate.sh <q0_keep_rate> [out_dir]}"
RATE_TAG="${RATE//./}"
PY="${PYTHON:-./.venv/bin/python}"
MODEL_PATH="${MODEL_PATH:-$HOME/models/Qwen2.5-VL-7B-Instruct-4bit}"
RSS_GUARD_MB="${RSS_GUARD_MB:-9000}"
REFERENCE_DIR="${REFERENCE_DIR:-research/experiments/2026/artifacts/phase1_30Z_long_q0_kr067_20260424}"
OUT="${2:-research/experiments/2026/artifacts/phase1_30AB_long_q0_kr${RATE_TAG}}"

COLD_JSONL="$REFERENCE_DIR/cold_dense_long.jsonl"
COLD_SUMMARY="$REFERENCE_DIR/cold_dense_long_summary.json"

if [[ ! -f "$COLD_JSONL" || ! -f "$COLD_SUMMARY" ]]; then
  echo "[1.30AB] missing reusable long-bucket cold control in $REFERENCE_DIR" >&2
  exit 1
fi

mkdir -p "$OUT"

if [[ -f "$OUT/streaming_q0_candidate_long.jsonl" && -f "$OUT/streaming_q0_candidate_long_summary.json" ]]; then
  echo "[1.30AB] reusing existing streaming arm in $OUT"
else
  "$PY" scripts/run_phase1_30_sam_streaming.py \
    --allow-dirty \
    --stack streaming \
    --manifest research/benchmark_manifests/videomme_long_dev_holdout_v1.toml \
    --frame-count 8 \
    --max-tokens 32 \
    --model-path "$MODEL_PATH" \
    --rss-guard-mb "$RSS_GUARD_MB" \
    --output "$OUT/streaming_q0_candidate_long.jsonl" \
    --summary "$OUT/streaming_q0_candidate_long_summary.json" \
    --vision-tower-layer 2 \
    --vision-tower-keep-rate 0.50 \
    --vision-tower-keep-rate-first-query 1.0 \
    --vision-tower-keep-rate-first-query-long "$RATE" \
    --vision-tower-keep-rate-follow-ups 0.50 \
    --drift-refresh-policy off
fi

"$PY" scripts/analyze_phase1_30_sam_streaming_pair.py \
  --cold-jsonl "$COLD_JSONL" \
  --streaming-jsonl "$OUT/streaming_q0_candidate_long.jsonl" \
  --cold-summary "$COLD_SUMMARY" \
  --streaming-summary "$OUT/streaming_q0_candidate_long_summary.json" \
  --pair-summary "$OUT/pair_summary.json" \
  --per-clip-buckets "$OUT/per_clip_buckets.json" \
  --paired-queries "$OUT/paired_queries.jsonl"
