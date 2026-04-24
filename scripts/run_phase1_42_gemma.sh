#!/usr/bin/env bash
# Phase 1.42 — Gemma 4 Track A transfer to motion holdouts.
#
# Runs:
#  1. a single-item VideoMME smoke to catch geometry/generate regressions
#  2. TOMATO motion holdout N=30 with Planner 2.0 base
#  3. MVBench motion holdout N=30 with Planner 2.0 base

set -euo pipefail

cd "$(dirname "$0")/.."

PY="${PYTHON:-./.venv/bin/python}"
MODEL_PATH="${GEMMA_MODEL_PATH:-$HOME/models/gemma-4-e4b-it-4bit}"
SMOKE_MANIFEST="${PHASE1_42_SMOKE_MANIFEST:-research/benchmark_manifests/videomme_dev_v1_single_item.toml}"
OUT_ROOT="${PHASE1_42_OUT_ROOT:-research/experiments/2026/artifacts}"

if [ ! -e "$MODEL_PATH" ]; then
  echo "missing Gemma model path: $MODEL_PATH" >&2
  exit 1
fi

run_cached() {
  local benchmark="$1"
  local manifest="$2"
  local out_dir="$3"
  mkdir -p "$out_dir"
  "$PY" scripts/run_benchmark_track_a.py run \
    --benchmark "$benchmark" \
    --manifest "$manifest" \
    --chunk-size 1 \
    --frame-count 8 \
    --max-tokens 32 \
    --cache-mode default \
    --statistic max_abs \
    --static-threshold 8 \
    --shifted-threshold 32 \
    --reuse-classes static,shifted \
    --max-age 4 \
    --model-path "$MODEL_PATH" \
    --no-feature-replay \
    --output-path "$out_dir/results.jsonl" \
    --summary-path "$out_dir/summary.json"
}

echo "[1.42] smoke"
run_cached \
  videomme \
  "$SMOKE_MANIFEST" \
  "$OUT_ROOT/phase1_42_gemma_smoke"

echo "[1.42] TOMATO motion holdout"
run_cached \
  tomato \
  research/benchmark_manifests/tomato_motion_holdout_v2.toml \
  "$OUT_ROOT/phase1_42_gemma_tomato_motion_holdout_v2_cached"

echo "[1.42] MVBench motion holdout"
run_cached \
  mvbench \
  research/benchmark_manifests/mvbench_motion_holdout_v2.toml \
  "$OUT_ROOT/phase1_42_gemma_mvbench_motion_holdout_v2_cached"
