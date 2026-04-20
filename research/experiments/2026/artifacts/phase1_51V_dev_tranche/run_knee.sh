#!/usr/bin/env bash
# 1.51V knee search: layer ∈ {2, 3, 4} at kr=0.50.
# Goal: find layer where V_red ≥ 35% AND accuracy preserved.
set -euo pipefail

cd "$(dirname "$0")/../../../../.."

MANIFEST="research/benchmark_manifests/videomme_dev_v1_stage2_subset.toml"
OUT="research/experiments/2026/artifacts/phase1_51V_dev_tranche"
PY=".venv/bin/python"
DRIVER="scripts/run_novelty_pruning_gemma.py"
COMMON_ARGS="--manifest $MANIFEST --anchor-arm none --keep-rate 1.0 --frame-count 8 --rss-guard-mb 10000 --max-tokens 32"

run_cell() {
  local name="$1"; shift
  echo "=== [$(date +%H:%M:%S)] Running $name ==="
  $PY $DRIVER $COMMON_ARGS "$@" \
    --output "$OUT/${name}.jsonl" \
    --summary "$OUT/${name}_summary.json" \
    >"$OUT/${name}.log" 2>&1
  echo "    done $name"
}

for L in 2 3 4; do
  run_cell "L${L}_kr050" --vision-tower-layer $L --vision-tower-keep-rate 0.50
done

echo "=== Knee search done at $(date +%H:%M:%S) ==="
