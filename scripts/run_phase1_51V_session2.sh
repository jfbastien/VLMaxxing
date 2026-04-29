#!/usr/bin/env bash
# Phase 1.51V session 2 — 32f probe + EXP10 holdout replication, 4 experiments.
# Preregistered 2026-04-21:
#   - research/experiments/2026/2026-04-21-phase-1_51V-32f-probe-prereg.md (EXP13/14)
#   - research/experiments/2026/2026-04-21-phase-1_51R-closure-post-1_51V.md promotion rule (EXP15/16)
#
# Replaces the n=60 same-set replication (VideoMME dev v1 has 30 items;
# holdout v1 has 30 disjoint items — a cleaner transfer test).
#
# Each experiment is idempotent (skips if <name>.done exists).
#
# Usage: .venv/bin/bash scripts/run_phase1_51V_session2.sh
# Sandbox: requires Metal; launch with dangerouslyDisableSandbox=true.

set -euo pipefail

cd "$(dirname "$0")/.."

OUT="research/experiments/2026/artifacts/phase1_51V_session2"
mkdir -p "$OUT"

PY=".venv/bin/python"
DRIVER="scripts/run_novelty_pruning_gemma.py"

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

log "=== Phase 1.51V session 2 queue start ==="

# --- Tier A: 32-frame probe (H_fsscale follow-on) ---
run_exp "exp13_videomme_32f_unpatched" \
  --manifest research/benchmark_manifests/videomme_dev_v1.toml \
  --frame-count 32 --anchor-arm none --keep-rate 1.0 \
  $COMMON

run_exp "exp14_videomme_32f_L2_kr050" \
  --manifest research/benchmark_manifests/videomme_dev_v1.toml \
  --frame-count 32 --anchor-arm none --keep-rate 1.0 \
  --vision-tower-layer 2 --vision-tower-keep-rate 0.50 \
  $COMMON

# --- Tier B: EXP10 promotion gate on HOLDOUT (n=30 disjoint) ---
# Thermal anchor: V-alone at L=2 kr_V=0.50 on holdout, then composition.
run_exp "exp15_videomme_holdout_8f_L2_kr050" \
  --manifest research/benchmark_manifests/videomme_holdout_v1.toml \
  --frame-count 8 --anchor-arm none --keep-rate 1.0 \
  --vision-tower-layer 2 --vision-tower-keep-rate 0.50 \
  $COMMON

run_exp "exp16_videomme_holdout_8f_L2_kr050_novelty030_none" \
  --manifest research/benchmark_manifests/videomme_holdout_v1.toml \
  --frame-count 8 --anchor-arm none --keep-rate 0.3 \
  --vision-tower-layer 2 --vision-tower-keep-rate 0.50 \
  $COMMON

log "=== Phase 1.51V session 2 queue COMPLETE ==="
touch "$OUT/queue.done"
