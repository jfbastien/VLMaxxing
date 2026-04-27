#!/usr/bin/env bash
# Phase 1.55F-stage-timing — analysis-only adaptive-vs-fixed attribution.

set -euo pipefail

cd "$(dirname "$0")/.."

PY="${PYTHON:-./.venv/bin/python}"
OUT_DIR="${PHASE1_55F_STAGE_TIMING_OUT_DIR:-research/experiments/2026/artifacts/phase1_55F_stage_timing}"

mkdir -p "$OUT_DIR"

"$PY" scripts/analyze_phase1_55f_stage_timing.py \
  --output "$OUT_DIR/stage_timing_summary.json"
