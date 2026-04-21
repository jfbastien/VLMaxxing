#!/usr/bin/env bash
# Phase 1.51V session 4 — V-only MVBench + TOMATO holdout pairs (EXP19-22).
# Preregistered 2026-04-21:
#   research/experiments/2026/2026-04-21-phase-1_51V-session4-prereg.md
#
# Rationale: session 3 (EXP17/18) passed all 4 hypotheses on VideoMME 8f
# holdout with a clean thermal pair. Session 4 extends the same pattern to
# MVBench motion holdout v2 + TOMATO motion holdout v2, so the C-VISION
# paper-table cells on ALL three benchmarks drop the "dev-only n=30" caveat.
# Runs unpatched arm first in each pair (per session-3 thermal lesson).
#
# Each experiment is idempotent (skips if <name>.done exists).
#
# Usage: .venv/bin/bash scripts/run_phase1_51V_session4.sh
# Sandbox: requires Metal; launch with dangerouslyDisableSandbox=true.

set -euo pipefail

cd "$(dirname "$0")/.."

OUT="research/experiments/2026/artifacts/phase1_51V_session4"
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

log "=== Phase 1.51V session 4 queue start ==="

# MVBench pair: EXP19 unpatched (longer, runs first per session-3 thermal lesson)
#               EXP20 V-patched (back-to-back)
run_exp "exp19_mvbench_holdout_8f_unpatched" \
  --manifest research/benchmark_manifests/mvbench_motion_holdout_v2.toml \
  --frame-count 8 --anchor-arm none --keep-rate 1.0 \
  $COMMON

run_exp "exp20_mvbench_holdout_8f_L2_kr050" \
  --manifest research/benchmark_manifests/mvbench_motion_holdout_v2.toml \
  --frame-count 8 --anchor-arm none --keep-rate 1.0 \
  --vision-tower-layer 2 --vision-tower-keep-rate 0.50 \
  $COMMON

# TOMATO pair: EXP21 unpatched first, EXP22 V-patched back-to-back.
run_exp "exp21_tomato_holdout_8f_unpatched" \
  --manifest research/benchmark_manifests/tomato_motion_holdout_v2.toml \
  --frame-count 8 --anchor-arm none --keep-rate 1.0 \
  $COMMON

run_exp "exp22_tomato_holdout_8f_L2_kr050" \
  --manifest research/benchmark_manifests/tomato_motion_holdout_v2.toml \
  --frame-count 8 --anchor-arm none --keep-rate 1.0 \
  --vision-tower-layer 2 --vision-tower-keep-rate 0.50 \
  $COMMON

log "=== Phase 1.51V session 4 queue COMPLETE ==="
touch "$OUT/queue.done"
