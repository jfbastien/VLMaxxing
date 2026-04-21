#!/usr/bin/env bash
# Phase 1.51V session 5 — TOMATO holdout V-only rerun (EXP23/24).
# Preregistered 2026-04-21:
#   research/experiments/2026/2026-04-21-phase-1_51V-session5-prereg.md
#
# Rationale: session 4 EXP21/22 TOMATO pair was thermally confounded
# (decode Δ 206 ms = 6.52% on 3164 ms window) + 4 dense-arm runtime
# outliers. Session 5 reruns the pair under the revised thermal gate
# `|decode Δ| < max(0.02 × decode_ms, 100 ms)` with an extended
# cool-down before launch.
#
# Each experiment is idempotent (skips if <name>.done exists).
#
# Usage: .venv/bin/bash scripts/run_phase1_51V_session5.sh
# Sandbox: requires Metal; launch with dangerouslyDisableSandbox=true.

set -euo pipefail

cd "$(dirname "$0")/.."

OUT="research/experiments/2026/artifacts/phase1_51V_session5"
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

log "=== Phase 1.51V session 5 queue start ==="

# TOMATO pair: EXP23 unpatched first (longer), EXP24 V-patched back-to-back.
run_exp "exp23_tomato_holdout_8f_unpatched" \
  --manifest research/benchmark_manifests/tomato_motion_holdout_v2.toml \
  --frame-count 8 --anchor-arm none --keep-rate 1.0 \
  $COMMON

run_exp "exp24_tomato_holdout_8f_L2_kr050" \
  --manifest research/benchmark_manifests/tomato_motion_holdout_v2.toml \
  --frame-count 8 --anchor-arm none --keep-rate 1.0 \
  --vision-tower-layer 2 --vision-tower-keep-rate 0.50 \
  $COMMON

log "=== Phase 1.51V session 5 queue COMPLETE ==="
touch "$OUT/queue.done"
