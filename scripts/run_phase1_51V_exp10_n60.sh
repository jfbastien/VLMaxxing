#!/usr/bin/env bash
# Phase 1.51V EXP10 n=60 — H_stack composition re-check on pooled
# VideoMME dev+holdout manifest (task #152).
# Preregistered 2026-04-21:
#   research/experiments/2026/2026-04-21-phase-1_51V-exp10-n60-prereg.md
#
# Rationale: H_stack (V-patching × novelty-pruning) has two n=30 landings
# that straddle the 1.10× paper-reopener threshold (dev 1.11× / holdout
# 1.064×). EXP10 n=60 on the combined dev+holdout manifest yields the
# weighted-average answer the paper actually claims when it says
# "H_stack on VideoMME".
#
# Each experiment is idempotent (skips if <name>.done exists).
#
# Usage: .venv/bin/bash scripts/run_phase1_51V_exp10_n60.sh
# Sandbox: requires Metal; launch with dangerouslyDisableSandbox=true.

set -euo pipefail

cd "$(dirname "$0")/.."

OUT="research/experiments/2026/artifacts/phase1_51V_exp10_n60"
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
COMMON="--model-path $GEMMA_MODEL_PATH --frame-count 8 --max-tokens 32 --rss-guard-mb 10000"
MANIFEST="research/benchmark_manifests/videomme_combined_v1_n60.toml"
VT_FLAGS="--vision-tower-layer 2 --vision-tower-keep-rate 0.50"

log "=== Phase 1.51V EXP10 n=60 H_stack composition re-check queue start ==="

# EXP_a reference (V-patched, novelty disabled): runs first cold-to-lukewarm.
run_exp "exp10n60_a_vonly_ref" \
  --manifest "$MANIFEST" \
  $VT_FLAGS --anchor-arm none --keep-rate 1.0 \
  $COMMON

# EXP_b H_stack (V-patched + novelty kr=0.30): paired back-to-back.
run_exp "exp10n60_b_vplus_novelty030" \
  --manifest "$MANIFEST" \
  $VT_FLAGS --anchor-arm none --keep-rate 0.30 \
  $COMMON

log "=== Phase 1.51V EXP10 n=60 queue COMPLETE ==="
touch "$OUT/queue.done"
