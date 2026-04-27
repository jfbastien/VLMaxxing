#!/usr/bin/env bash
# Phase 1.30AF — post-hoc attribution for the 1.30AC/AD boundary result.

set -euo pipefail

cd "$(dirname "$0")/.."

PY="${PYTHON:-./.venv/bin/python}"
OUT_DIR="${PHASE1_30AF_OUT_DIR:-research/experiments/2026/artifacts/phase1_30AF_cache_boundary_attribution}"

mkdir -p "$OUT_DIR"

"$PY" scripts/analyze_phase1_30_cache_boundary_attribution.py \
  --output "$OUT_DIR/attribution_summary.json"
