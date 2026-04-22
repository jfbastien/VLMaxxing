#!/usr/bin/env bash
# Phase 1.55D v2 selective re-prefill runner.
#
# Usage:
#   .venv/bin/bash scripts/run_phase1_55D_v2.sh

set -euo pipefail

cd "$(dirname "$0")/.."

PY="${PYTHON:-./.venv/bin/python}"
OUT_DIR="research/experiments/2026/artifacts/phase1_55D_selective_reprefill_v2"

mkdir -p "$OUT_DIR"

"$PY" scripts/run_kv_selective_reprefill_v2.py \
  --mode both \
  --video-ids 037,100,116,120,158,160,210 \
  --frame-count 20 \
  --reprefill-k 4 \
  --max-tokens 32 \
  --output-dir "$OUT_DIR"
