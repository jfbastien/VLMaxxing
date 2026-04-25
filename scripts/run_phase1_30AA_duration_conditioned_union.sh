#!/usr/bin/env bash
# Phase 1.30AA duration-conditioned full-union rerun.
#
# Policy under test:
# - Q0 short/medium: dense (kr=1.0)
# - Q0 long: cheaper candidate (kr=0.67)
# - follow-ups: kr=0.50
#
# This is the first fully measured, no-splice version of the policy family
# suggested by 1.30X/1.30Y. Run this only after 1.30Z keeps the long bucket
# inside the preregistered rescue/format band.
#
# Runtime estimate on the current Qwen 7B / 8f setup:
# - cold full union: ~4-5 h
# - streaming full union: ~1.5-2.5 h
# - paired analysis: <1 min

set -euo pipefail

cd "$(dirname "$0")/.."

PY="${PYTHON:-./.venv/bin/python}"
MODEL_PATH="${MODEL_PATH:-$HOME/models/Qwen2.5-VL-7B-Instruct-4bit}"
RSS_GUARD_MB="${RSS_GUARD_MB:-9000}"
OUT="${OUT:-research/experiments/2026/artifacts/phase1_30AA_duration_conditioned_union}"

mkdir -p "$OUT"

if [[ -f "$OUT/cold_dense.jsonl" && -f "$OUT/cold_dense_summary.json" ]]; then
  echo "[1.30AA] reusing existing cold arm in $OUT"
else
  "$PY" scripts/run_phase1_30_sam_streaming.py \
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
  echo "[1.30AA] reusing existing streaming arm in $OUT"
else
  "$PY" scripts/run_phase1_30_sam_streaming.py \
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
    --vision-tower-keep-rate-first-query-long 0.67 \
    --vision-tower-keep-rate-follow-ups 0.50 \
    --drift-refresh-policy off
fi

"$PY" scripts/analyze_phase1_30_sam_streaming_pair.py \
  --cold-jsonl "$OUT/cold_dense.jsonl" \
  --streaming-jsonl "$OUT/streaming_duration_conditioned.jsonl" \
  --cold-summary "$OUT/cold_dense_summary.json" \
  --streaming-summary "$OUT/streaming_duration_conditioned_summary.json" \
  --pair-summary "$OUT/pair_summary.json" \
  --per-clip-buckets "$OUT/per_clip_buckets.json" \
  --paired-queries "$OUT/paired_queries.jsonl"
