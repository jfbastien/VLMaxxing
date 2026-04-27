#!/usr/bin/env bash
# Phase 1.66 — analysis-only memory characterization.

set -euo pipefail

cd "$(dirname "$0")/.."

PY="${PYTHON:-./.venv/bin/python}"
OUT_DIR="${PHASE1_66_OUT_DIR:-research/experiments/2026/artifacts/phase1_66_memory_characterization}"

mkdir -p "$OUT_DIR"

"$PY" scripts/analyze_phase1_66_memory_characterization.py \
  --output "$OUT_DIR/memory_characterization_summary.json" \
  --csv-output "$OUT_DIR/memory_cells.csv"
