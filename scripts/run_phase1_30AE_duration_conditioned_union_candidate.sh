#!/usr/bin/env bash
# Phase 1.30AE — duration-conditioned full-union rerun with a sweep-selected
# long-bucket Q0 keep rate.
#
# Why this exists:
# - 1.30AB locates the long-bucket Q0 rate boundary.
# - 1.30AE is the first fully measured no-splice full-union rerun using that
#   selected boundary rate.
#
# Usage:
#   ./scripts/run_phase1_30AE_duration_conditioned_union_candidate.sh 0.80
#   ./scripts/run_phase1_30AE_duration_conditioned_union_candidate.sh 0.85 /tmp/outdir
#
# Runtime estimate:
# - cold full union: ~4-5 h
# - streaming full union: ~1.5-2.5 h
# - paired analysis: <1 min

set -euo pipefail

cd "$(dirname "$0")/.."

RATE="${1:?usage: run_phase1_30AE_duration_conditioned_union_candidate.sh <long_q0_keep_rate> [out_dir]}"
RATE_TAG="${RATE//./}"
PY="${PYTHON:-./.venv/bin/python}"
MODEL_PATH="${MODEL_PATH:-$HOME/models/Qwen2.5-VL-7B-Instruct-4bit}"
RSS_GUARD_MB="${RSS_GUARD_MB:-9000}"
OUT="${2:-research/experiments/2026/artifacts/phase1_30AE_duration_conditioned_union_kr${RATE_TAG}}"

mkdir -p "$OUT"

if [[ -f "$OUT/cold_dense.jsonl" && -f "$OUT/cold_dense_summary.json" ]]; then
  echo "[1.30AE] reusing existing cold arm in $OUT"
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

if [[ -f "$OUT/streaming_duration_conditioned.jsonl" && -f "$OUT/streaming_duration_conditioned_summary.json" ]]; then
  echo "[1.30AE] reusing existing streaming arm in $OUT"
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
    --output "$OUT/streaming_duration_conditioned.jsonl" \
    --summary "$OUT/streaming_duration_conditioned_summary.json" \
    --vision-tower-layer 2 \
    --vision-tower-keep-rate 0.50 \
    --vision-tower-keep-rate-first-query 1.0 \
    --vision-tower-keep-rate-first-query-short 1.0 \
    --vision-tower-keep-rate-first-query-medium 1.0 \
    --vision-tower-keep-rate-first-query-long "$RATE" \
    --vision-tower-keep-rate-follow-ups 0.50 \
    --drift-refresh-policy off
fi

"$PY" scripts/analyze_phase1_30_scaleout_streaming_pair.py \
  --cold-jsonl "$OUT/cold_dense.jsonl" \
  --streaming-jsonl "$OUT/streaming_duration_conditioned.jsonl" \
  --cold-summary "$OUT/cold_dense_summary.json" \
  --streaming-summary "$OUT/streaming_duration_conditioned_summary.json" \
  --pair-summary "$OUT/pair_summary.json" \
  --per-clip-buckets "$OUT/per_clip_buckets.json" \
  --paired-queries "$OUT/paired_queries.jsonl"
