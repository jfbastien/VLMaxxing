#!/usr/bin/env bash
# 1.51V dev tranche: layer ∈ {1, 6, 12} × keep_rate ∈ {0.25, 0.50, 0.75} on 5-item subset.
# Plus a control (unpatched) baseline over the same 5 items.
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

# Control (unpatched) baseline
run_cell "control_nopatch"

# 9 patched cells
for L in 1 6 12; do
  for KR in 0.25 0.50 0.75; do
    KR_SHORT="${KR//./}"
    run_cell "L${L}_kr${KR_SHORT}" --vision-tower-layer $L --vision-tower-keep-rate $KR
  done
done

echo "=== All cells done at $(date +%H:%M:%S) ==="
