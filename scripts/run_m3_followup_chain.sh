#!/usr/bin/env bash
# Chained M3 follow-up driver.
#
# Runs the four M3 scripts serially per codex's recommendation. set -e is
# strict on purpose: any sidecar-equivalence gate failure must abort, because
# the M5 launchers refuse to run without a passing M3 gate. The TOMATO kr=0.9
# smoke is diagnostic-only; if it fails we still want to know, so we let
# strict mode catch it too.
#
# Order:
#   1. Qwen 8f sidecar equivalence  (~20 min)
#   2. Qwen 16f sidecar equivalence (~30 min)
#   3. Gemma 8f sidecar equivalence (~25 min)
#   4. TOMATO kr=0.9 balanced N=9 boundary smoke (~60 min)
#
# Estimated total wall-clock: ~2h15m on the M3.

set -euo pipefail
LAST_PHASE=""
trap 'echo "[m3-chain] $LAST_PHASE failed at $(date -u +%Y-%m-%dT%H:%M:%SZ)"' ERR

cd "$(dirname "$0")/.."

START_TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
echo "[m3-chain] start $START_TS"
echo "[m3-chain] phases: qwen_8f_gate, qwen_16f_gate, gemma_8f_gate, tomato_kr090_smoke"

run_phase() {
  local name="$1"
  shift
  LAST_PHASE="$name"
  echo "[m3-chain] === phase=$name start $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  "$@"
  echo "[m3-chain] === phase=$name done $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
}

run_phase qwen_8f_gate   bash scripts/run_ov6_sidecar_equivalence.sh
run_phase qwen_16f_gate  env OV6S_FRAME_COUNT=16 bash scripts/run_ov6_sidecar_equivalence.sh
run_phase gemma_8f_gate  bash scripts/run_ov6_gemma_sidecar_equivalence.sh
run_phase tomato_kr090   bash scripts/run_ov6_tomato_kr090_boundary_smoke.sh

END_TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
echo "[m3-chain] end $END_TS"
