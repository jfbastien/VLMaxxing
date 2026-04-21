#!/usr/bin/env bash
# Phase 1.51V session 3 — V-only holdout unpatched vs V-patched pair (EXP17/18).
# Preregistered 2026-04-21:
#   research/experiments/2026/2026-04-21-phase-1_51V-session3-prereg.md
#
# Rationale: session 2 (EXP15/16) did not measure V-only on holdout; EXP15 is a
# V-patched reference (novelty=1.0), not an unpatched baseline. Session 3 closes
# the gap with a thermally-paired unpatched/patched pair on VideoMME holdout v1
# 8f. EXP18 is a fresh re-run of EXP15's config, paired with EXP17 in the same
# session so the thermal-pairing invariant (decode Delta < 2%) can hold.
#
# Each experiment is idempotent (skips if <name>.done exists).
#
# Usage: .venv/bin/bash scripts/run_phase1_51V_session3.sh
# Sandbox: requires Metal; launch with dangerouslyDisableSandbox=true.

set -euo pipefail

cd "$(dirname "$0")/.."

OUT="research/experiments/2026/artifacts/phase1_51V_session3"
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

COMMON="--model-path /Users/jfb/models/gemma-4-e4b-it-4bit --max-tokens 32 --rss-guard-mb 10000"

log "=== Phase 1.51V session 3 queue start ==="

# EXP17: unpatched holdout baseline (no vision-tower slice).
run_exp "exp17_videomme_holdout_8f_unpatched" \
  --manifest research/benchmark_manifests/videomme_holdout_v1.toml \
  --frame-count 8 --anchor-arm none --keep-rate 1.0 \
  $COMMON

# EXP18: V-patched holdout (fresh re-run of EXP15 config, thermally paired with EXP17).
run_exp "exp18_videomme_holdout_8f_L2_kr050" \
  --manifest research/benchmark_manifests/videomme_holdout_v1.toml \
  --frame-count 8 --anchor-arm none --keep-rate 1.0 \
  --vision-tower-layer 2 --vision-tower-keep-rate 0.50 \
  $COMMON

log "=== Phase 1.51V session 3 queue COMPLETE ==="
touch "$OUT/queue.done"
