#!/usr/bin/env bash
# Phase 1.42 — Gemma Track B dense baselines.
#
# Intended to run only after the Phase 1.42 Track A fidelity gate passes.
# Measures dense stage shares on the same two motion holdout manifests so the
# Gemma transfer result can immediately feed the Track B ceiling analysis.

set -euo pipefail

cd "$(dirname "$0")/.."

PY="${PYTHON:-./.venv/bin/python}"
MODEL_PATH="${GEMMA_MODEL_PATH:-$HOME/models/gemma-4-e4b-it-4bit}"
OUT_ROOT="${PHASE1_42_TRACK_B_OUT_ROOT:-results/track_b}"

if [ ! -e "$MODEL_PATH" ]; then
  echo "missing Gemma model path: $MODEL_PATH" >&2
  exit 1
fi

mkdir -p "$OUT_ROOT"

run_dense() {
  local manifest="$1"
  local stem="$2"
  "$PY" scripts/run_track_b.py \
    --manifest "$manifest" \
    --frame-count 8 \
    --mode mc_scoring \
    --max-tokens 32 \
    --model-path "$MODEL_PATH" \
    --output "$OUT_ROOT/${stem}.jsonl" \
    --summary "$OUT_ROOT/${stem}.json"
}

echo "[1.42/TrackB] TOMATO motion holdout dense baseline"
run_dense \
  research/benchmark_manifests/tomato_motion_holdout_v2.toml \
  gemma_tomato_mc_n30

echo "[1.42/TrackB] MVBench motion holdout dense baseline"
run_dense \
  research/benchmark_manifests/mvbench_motion_holdout_v2.toml \
  gemma_mvbench_mc_n30
