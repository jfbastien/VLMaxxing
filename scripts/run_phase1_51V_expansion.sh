#!/usr/bin/env bash
# Phase 1.51V expansion queue — 12 experiments, ~7.7h, back-to-back.
# Preregistered 2026-04-20 in research/experiments/2026/2026-04-20-phase-1_51V-expansion-prereg.md
#
# Each experiment is idempotent (skips if <name>.done exists). Outputs under
# research/experiments/2026/artifacts/phase1_51V_expansion/.
#
# Usage: .venv/bin/bash scripts/run_phase1_51V_expansion.sh
# Sandbox: requires Metal; launch with dangerouslyDisableSandbox=true.

set -euo pipefail

# Repo root
cd "$(dirname "$0")/.."

OUT="research/experiments/2026/artifacts/phase1_51V_expansion"
mkdir -p "$OUT"

PY=".venv/bin/python"
DRIVER="scripts/run_novelty_pruning_gemma.py"

# Global queue sentinel — written at end for loop to detect completion
QUEUE_LOG="$OUT/queue.log"
: >"$QUEUE_LOG.tmp" && mv "$QUEUE_LOG.tmp" "$QUEUE_LOG" 2>/dev/null || true

log() {
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*" | tee -a "$QUEUE_LOG"
}

run_exp() {
  local name="$1"; shift
  if [ -f "$OUT/${name}.done" ]; then
    log "SKIP  $name (already done)"
    return 0
  fi
  log "START $name"
  local t0=$(date +%s)
  if $PY $DRIVER "$@" \
       --output "$OUT/${name}.jsonl" \
       --summary "$OUT/${name}_summary.json" \
       >"$OUT/${name}.log" 2>&1; then
    local t1=$(date +%s)
    touch "$OUT/${name}.done"
    log "DONE  $name ($((t1 - t0))s)"
  else
    local rc=$?
    log "FAIL  $name (exit=$rc, see $OUT/${name}.log)"
    return $rc
  fi
}

: "${GEMMA_MODEL_PATH:?Set GEMMA_MODEL_PATH to the Gemma 4 E4B 4-bit model path or model id}"
COMMON="--model-path $GEMMA_MODEL_PATH --max-tokens 32 --rss-guard-mb 10000"

log "=== Phase 1.51V expansion queue start ==="

# --- Tier 0: thermally-paired VideoMME 8f confirmation ---
run_exp "exp01_videomme_8f_unpatched" \
  --manifest research/benchmark_manifests/videomme_dev_v1.toml \
  --frame-count 8 --anchor-arm none --keep-rate 1.0 \
  $COMMON

run_exp "exp02_videomme_8f_L2_kr050" \
  --manifest research/benchmark_manifests/videomme_dev_v1.toml \
  --frame-count 8 --anchor-arm none --keep-rate 1.0 \
  --vision-tower-layer 2 --vision-tower-keep-rate 0.50 \
  $COMMON

# --- Tier 1: L=2 Pareto completion on VideoMME 8f ---
run_exp "exp03_videomme_8f_L2_kr025" \
  --manifest research/benchmark_manifests/videomme_dev_v1.toml \
  --frame-count 8 --anchor-arm none --keep-rate 1.0 \
  --vision-tower-layer 2 --vision-tower-keep-rate 0.25 \
  $COMMON

run_exp "exp04_videomme_8f_L2_kr075" \
  --manifest research/benchmark_manifests/videomme_dev_v1.toml \
  --frame-count 8 --anchor-arm none --keep-rate 1.0 \
  --vision-tower-layer 2 --vision-tower-keep-rate 0.75 \
  $COMMON

# --- Tier 2: Cross-benchmark transfer ---
run_exp "exp05_mvbench_8f_unpatched" \
  --manifest research/benchmark_manifests/mvbench_motion_dev_v2.toml \
  --frame-count 8 --anchor-arm none --keep-rate 1.0 \
  $COMMON

run_exp "exp06_mvbench_8f_L2_kr050" \
  --manifest research/benchmark_manifests/mvbench_motion_dev_v2.toml \
  --frame-count 8 --anchor-arm none --keep-rate 1.0 \
  --vision-tower-layer 2 --vision-tower-keep-rate 0.50 \
  $COMMON

run_exp "exp07_tomato_8f_unpatched" \
  --manifest research/benchmark_manifests/tomato_motion_dev_v2.toml \
  --frame-count 8 --anchor-arm none --keep-rate 1.0 \
  $COMMON

run_exp "exp08_tomato_8f_L2_kr050" \
  --manifest research/benchmark_manifests/tomato_motion_dev_v2.toml \
  --frame-count 8 --anchor-arm none --keep-rate 1.0 \
  --vision-tower-layer 2 --vision-tower-keep-rate 0.50 \
  $COMMON

# --- Tier 3: 1.51R anchor re-run on V-patched features ---
run_exp "exp09_videomme_8f_L2_kr050_novelty050_structural" \
  --manifest research/benchmark_manifests/videomme_dev_v1.toml \
  --frame-count 8 --anchor-arm gemma_structural --keep-rate 0.5 \
  --vision-tower-layer 2 --vision-tower-keep-rate 0.50 \
  $COMMON

run_exp "exp10_videomme_8f_L2_kr050_novelty030_none" \
  --manifest research/benchmark_manifests/videomme_dev_v1.toml \
  --frame-count 8 --anchor-arm none --keep-rate 0.3 \
  --vision-tower-layer 2 --vision-tower-keep-rate 0.50 \
  $COMMON

# --- Tier 4: Frame-scaling probe ---
run_exp "exp11_videomme_16f_unpatched" \
  --manifest research/benchmark_manifests/videomme_dev_v1.toml \
  --frame-count 16 --anchor-arm none --keep-rate 1.0 \
  $COMMON

run_exp "exp12_videomme_16f_L2_kr050" \
  --manifest research/benchmark_manifests/videomme_dev_v1.toml \
  --frame-count 16 --anchor-arm none --keep-rate 1.0 \
  --vision-tower-layer 2 --vision-tower-keep-rate 0.50 \
  $COMMON

log "=== Phase 1.51V expansion queue COMPLETE ==="
touch "$OUT/queue.done"
