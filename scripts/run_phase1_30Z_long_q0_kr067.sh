#!/usr/bin/env bash
# Phase 1.30Z long-bucket continuation.
#
# Why this exists:
# - 1.30Y promoted kr_Q0=0.67 from a residual-pair scout to a real
#   long-bucket candidate.
# - This run is the required generalization test before the full
#   duration-conditioned union rerun (1.30AA).
#
# Runtime estimate on the current Qwen 7B / 8f setup:
# - cold long bucket: ~2.5-3.5 h
# - streaming long bucket: ~1-1.5 h
# - paired analysis: <1 min

set -euo pipefail

cd "$(dirname "$0")/.."

PY="${PYTHON:-./.venv/bin/python}"
MODEL_PATH="${MODEL_PATH:-$HOME/models/Qwen2.5-VL-7B-Instruct-4bit}"
RSS_GUARD_MB="${RSS_GUARD_MB:-10000}"
OUT="${OUT:-research/experiments/2026/artifacts/phase1_30Z_long_q0_kr067_20260424}"

mkdir -p "$OUT"

if [[ -f "$OUT/cold_dense_long.jsonl" && -f "$OUT/cold_dense_long_summary.json" ]]; then
  echo "[1.30Z] reusing existing cold arm in $OUT"
else
  "$PY" scripts/run_phase1_30_sam_streaming.py \
    --stack cold \
    --manifest research/benchmark_manifests/videomme_long_dev_holdout_v1.toml \
    --frame-count 8 \
    --max-tokens 32 \
    --model-path "$MODEL_PATH" \
    --rss-guard-mb "$RSS_GUARD_MB" \
    --output "$OUT/cold_dense_long.jsonl" \
    --summary "$OUT/cold_dense_long_summary.json" \
    --vision-tower-keep-rate 1.0 \
    --drift-refresh-policy off
fi

if [[ -f "$OUT/streaming_q0_kr067_followup_kr050_long.jsonl" && -f "$OUT/streaming_q0_kr067_followup_kr050_long_summary.json" ]]; then
  echo "[1.30Z] reusing existing streaming arm in $OUT"
else
  "$PY" scripts/run_phase1_30_sam_streaming.py \
    --stack streaming \
    --manifest research/benchmark_manifests/videomme_long_dev_holdout_v1.toml \
    --frame-count 8 \
    --max-tokens 32 \
    --model-path "$MODEL_PATH" \
    --rss-guard-mb "$RSS_GUARD_MB" \
    --output "$OUT/streaming_q0_kr067_followup_kr050_long.jsonl" \
    --summary "$OUT/streaming_q0_kr067_followup_kr050_long_summary.json" \
    --vision-tower-layer 2 \
    --vision-tower-keep-rate 0.50 \
    --vision-tower-keep-rate-first-query 1.0 \
    --vision-tower-keep-rate-first-query-long 0.67 \
    --vision-tower-keep-rate-follow-ups 0.50 \
    --drift-refresh-policy off
fi

"$PY" scripts/analyze_phase1_30_sam_streaming_pair.py \
  --cold-jsonl "$OUT/cold_dense_long.jsonl" \
  --streaming-jsonl "$OUT/streaming_q0_kr067_followup_kr050_long.jsonl" \
  --cold-summary "$OUT/cold_dense_long_summary.json" \
  --streaming-summary "$OUT/streaming_q0_kr067_followup_kr050_long_summary.json" \
  --pair-summary "$OUT/pair_summary.json" \
  --per-clip-buckets "$OUT/per_clip_buckets.json" \
  --paired-queries "$OUT/paired_queries.jsonl"
