#!/usr/bin/env bash
# Phase 1.57 holdout re-check runner.
#
# Re-runs the existing Qwen feature-drift measurement on the paired VideoMME
# holdout manifests so the paper's current "dev-only co-saturation" sentence
# can be validated or narrowed with explicit split-to-split evidence.
#
# Usage:
#   .venv/bin/bash scripts/run_phase1_57_holdout_recheck.sh
#
# Metal is not required for the current Qwen path; the script uses the
# cached-feature CPU workflow in scripts/measure_feature_drift.py.

set -euo pipefail

cd "$(dirname "$0")/.."

OUT="research/experiments/2026/artifacts/phase1_57_holdout_recheck"
mkdir -p "$OUT"

PY=".venv/bin/python"
MEASURE="scripts/measure_feature_drift.py"
COMPARE="scripts/compare_feature_drift.py"

run_measure() {
  local name="$1"; shift
  "$PY" "$MEASURE" "$@" --output "$OUT/${name}.json"
}

echo "[1.57] running 16f holdout re-check"
run_measure "qwen_16f_holdout" \
  --model qwen \
  --manifest research/benchmark_manifests/videomme_holdout_v1.toml \
  --frame-count 16

echo "[1.57] running 8f holdout re-check"
run_measure "qwen_8f_holdout" \
  --model qwen \
  --manifest research/benchmark_manifests/videomme_holdout_v1.toml \
  --frame-count 8

echo "[1.57] comparing dev vs holdout"
"$PY" "$COMPARE" \
  --summary research/experiments/2026/artifacts/phase1_57/qwen_8f_dev30.json \
  --summary "$OUT/qwen_8f_holdout.json" \
  > "$OUT/qwen_8f_compare.txt"

"$PY" "$COMPARE" \
  --summary research/experiments/2026/artifacts/phase1_57/qwen_16f_dev30.json \
  --summary "$OUT/qwen_16f_holdout.json" \
  > "$OUT/qwen_16f_compare.txt"

echo "[1.57] done"
