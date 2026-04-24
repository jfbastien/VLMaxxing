#!/usr/bin/env bash
# Phase 1.30W short-scout admission-policy runner.
#
# Tests the simplest evidence-backed rescue of the 1.30 streaming bridge:
# leave Q0 dense, prune Q2/Q3 at the validated 1.51V operating point.

set -euo pipefail

cd "$(dirname "$0")/.."

PY="${PYTHON:-./.venv/bin/python}"
MODEL_PATH="${MODEL_PATH:-$HOME/models/Qwen2.5-VL-7B-Instruct-4bit}"
RSS_GUARD_MB="${RSS_GUARD_MB:-10000}"
OUT="${OUT:-research/experiments/2026/artifacts/phase1_30W_q0_dense_followup_pruned_short}"

mkdir -p "$OUT"

"$PY" scripts/run_phase1_30_sam_streaming.py \
  --stack cold \
  --manifest research/benchmark_manifests/videomme_dev_v1_short_only.toml \
  --frame-count 8 \
  --max-tokens 32 \
  --model-path "$MODEL_PATH" \
  --rss-guard-mb "$RSS_GUARD_MB" \
  --output "$OUT/cold_dense.jsonl" \
  --summary "$OUT/cold_dense_summary.json" \
  --vision-tower-keep-rate 1.0 \
  --drift-refresh-policy off

"$PY" scripts/run_phase1_30_sam_streaming.py \
  --stack streaming \
  --manifest research/benchmark_manifests/videomme_dev_v1_short_only.toml \
  --frame-count 8 \
  --max-tokens 32 \
  --model-path "$MODEL_PATH" \
  --rss-guard-mb "$RSS_GUARD_MB" \
  --output "$OUT/streaming_q0_dense_followup_pruned_off.jsonl" \
  --summary "$OUT/streaming_q0_dense_followup_pruned_off_summary.json" \
  --vision-tower-layer 2 \
  --vision-tower-keep-rate 0.50 \
  --vision-tower-keep-rate-first-query 1.0 \
  --vision-tower-keep-rate-follow-ups 0.50 \
  --drift-refresh-policy off

"$PY" scripts/analyze_phase1_30_sam_streaming_pair.py \
  --cold-jsonl "$OUT/cold_dense.jsonl" \
  --streaming-jsonl "$OUT/streaming_q0_dense_followup_pruned_off.jsonl" \
  --cold-summary "$OUT/cold_dense_summary.json" \
  --streaming-summary "$OUT/streaming_q0_dense_followup_pruned_off_summary.json" \
  --pair-summary "$OUT/pair_summary.json" \
  --per-clip-buckets "$OUT/per_clip_buckets.json" \
  --paired-queries "$OUT/paired_queries.jsonl"
