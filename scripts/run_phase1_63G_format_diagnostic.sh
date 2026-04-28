#!/usr/bin/env bash
# Phase 1.63G-DIAG — Gemma Track B matched-format diagnostic.

set -euo pipefail

cd "$(dirname "$0")/.."

PY="${PYTHON:-./.venv/bin/python}"
OUT_DIR="${PHASE1_63G_OUT_DIR:-research/experiments/2026/artifacts/phase1_63G_gemma_track_b}"

"$PY" scripts/analyze_phase1_63g_format_diagnostic.py \
  --artifact-dir "$OUT_DIR" \
  --output "$OUT_DIR/format_diagnostic_summary.json"

echo "[1.63G-DIAG] wrote $OUT_DIR/format_diagnostic_summary.json"
