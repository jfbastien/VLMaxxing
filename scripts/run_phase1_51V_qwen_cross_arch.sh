#!/usr/bin/env bash
# Phase 1.51V Qwen cross-architecture pair.
#
# Usage:
#   .venv/bin/bash scripts/run_phase1_51V_qwen_cross_arch.sh

set -euo pipefail

cd "$(dirname "$0")/.."

OUT="research/experiments/2026/artifacts/phase1_51V_qwen_cross_arch"
mkdir -p "$OUT"

PY=".venv/bin/python"
DRIVER="scripts/run_phase1_51V.py"
ANALYZE="scripts/analyze_phase1_51V_pair.py"
COMMON="--manifest research/benchmark_manifests/videomme_dev_v1.toml --frame-count 8 --max-tokens 32 --model-path /Users/jfb/models/Qwen2.5-VL-7B-Instruct-4bit --rss-guard-mb 10000"

run_arm() {
  local name="$1"; shift
  "$PY" "$DRIVER" \
    $COMMON \
    --output "$OUT/${name}.jsonl" \
    --summary "$OUT/${name}_summary.json" \
    "$@"
}

echo "[1.51V-Qwen] unpatched arm"
run_arm "videomme_dev30_8f_unpatched"

echo "[1.51V-Qwen] patched arm"
run_arm "videomme_dev30_8f_L2_kr050" \
  --vision-tower-layer 2 \
  --vision-tower-keep-rate 0.50

echo "[1.51V-Qwen] analysis"
"$PY" "$ANALYZE" \
  --unpatched "$OUT/videomme_dev30_8f_unpatched_summary.json" \
  --patched "$OUT/videomme_dev30_8f_L2_kr050_summary.json" \
  > "$OUT/pair_analysis.txt"
