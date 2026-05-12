#!/usr/bin/env bash
# Meta-driver for the four preregistered follow-up experiments.
#
# Order matches the agreed launch sequence:
#   1. Qwen random multi-seed (~2.3h M3) — seed-stability for the
#      random>magnitude inversion at kr=0.5/layer=2/N=57.
#   2. Gemma codec smoke (~1h M3) — cross-family transfer at N=10.
#   3. Qwen TOMATO replication (~4h M3) — cross-benchmark Track B.
#   4. OV-3 H.264 calibration sensitivity (~4h M3) — pooled-vs-per-item
#      calibration robustness for Track A.
#
# Each child runner has its own skip-if-exists per arm, so this meta-driver
# can be restarted after a partial run. Use ERR trap so a single failing
# arm does not abort the entire sweep.

set -uo pipefail
trap 'echo "[meta] $LAST_PHASE failed at $(date -u +%Y-%m-%dT%H:%M:%SZ); continuing"' ERR

cd "$(dirname "$0")/.."

LAST_PHASE=""

START_TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
echo "[meta] start $START_TS"
echo "[meta] phases: random_multiseed, gemma_smoke, tomato_replication, h264_calibration"

run_phase() {
  local name="$1"
  local script="$2"
  LAST_PHASE="$name"
  echo "[meta] === phase=$name start $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  bash "$script"
  echo "[meta] === phase=$name done $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
}

run_phase random_multiseed scripts/run_ov6_qwen_random_multiseed.sh
run_phase gemma_smoke scripts/run_ov6_gemma_codec_smoke.sh
run_phase tomato_replication scripts/run_ov6_qwen_tomato_replication.sh
run_phase h264_calibration scripts/run_ov3_h264_calibration_sensitivity.sh

END_TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
echo "[meta] end $END_TS"
