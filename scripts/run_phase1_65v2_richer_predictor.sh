#!/usr/bin/env bash
# Phase 1.65v2 — richer dense-oracle predictor analysis on existing 1.65 rows.

set -euo pipefail

cd "$(dirname "$0")/.."

PY="${PYTHON:-./.venv/bin/python}"
INPUT="${PHASE1_65_SCORED_ROWS:-research/experiments/2026/artifacts/phase1_65_logit_margin_failure_predictor/scored_rows.jsonl}"
OUT_DIR="${PHASE1_65V2_OUT_DIR:-research/experiments/2026/artifacts/phase1_65v2_richer_predictor}"

mkdir -p "$OUT_DIR"

"$PY" scripts/analyze_phase1_65_richer_predictor.py \
  --scored-rows "$INPUT" \
  --output "$OUT_DIR/prediction_summary.json"

echo "[1.65v2] wrote $OUT_DIR/prediction_summary.json"
