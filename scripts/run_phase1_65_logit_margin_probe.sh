#!/usr/bin/env bash
# Phase 1.65 — dense logit-margin/failure-predictor scout.
#
# Re-scores a deterministic balanced sample of existing paired artifacts with
# dense Qwen answer-letter logprobs, then tests whether high dense margin
# predicts paired stability under the reuse policies.

set -euo pipefail

cd "$(dirname "$0")/.."

PY="${PYTHON:-./.venv/bin/python}"
MODEL_PATH="${PHASE1_65_MODEL_PATH:-$HOME/models/Qwen2.5-VL-7B-Instruct-4bit}"
OUT_DIR="${PHASE1_65_OUT_DIR:-research/experiments/2026/artifacts/phase1_65_logit_margin_failure_predictor}"
MAX_ROWS="${PHASE1_65_MAX_ROWS:-180}"
RSS_GUARD_MB="${RSS_GUARD_MB:-9000}"

"$PY" scripts/run_phase1_65_logit_margin_probe.py \
  --model-path "$MODEL_PATH" \
  --output-dir "$OUT_DIR" \
  --max-rows "$MAX_ROWS" \
  --rss-guard-mb "$RSS_GUARD_MB"
