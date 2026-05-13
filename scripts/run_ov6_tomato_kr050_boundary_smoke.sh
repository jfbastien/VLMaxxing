#!/usr/bin/env bash
# M3 OV-6 TOMATO motion kr=0.5/layer=2/N=10 boundary diagnostic smoke.
#
# Hypothesis disambiguation: in Phase 3 we observed that at kr=0.7/layer=2/
# frame=8 on TOMATO motion N=30, every prune scheme collapses near the
# chance floor (dense 0.267 -> magnitude 0.133, codec_novel_coded 0.167).
# Two possible causes:
#
#   H1: the frame budget is the boundary -- motion needs more than 8 frames
#       to be tractable for this model at any prune rate.
#   H2: the prune rate is the boundary -- kr=0.7 is too aggressive for
#       motion items; a milder prune (kr=0.5) preserves dense accuracy.
#
# This is the *opposite* keep-rate from Phase 3 (note: in our quota math
# kr=0.5 keeps fewer groups, kr=0.7 keeps more; for the Track B pruner the
# higher kr is the milder prune). So the experiment as-written below tests
# whether driving the prune more aggressively at kr=0.5 also stays at
# chance, which is the falsification path for H2 -- if even kr=0.5 holds
# above magnitude floor, prune rate is the lever; if kr=0.5 also collapses,
# the frame budget is the boundary.
#
# Preregistered gate:
#   H2 supported if either codec_novel_coded or magnitude_norm at this
#   keep rate exceeds 0.20 (i.e. above the Phase 3 collapse).
#   H1 supported if all sparse arms remain at or below the Phase 3
#   collapse band (<= 0.17).
#
# N=10 keeps M3 wall-clock under ~20 minutes per arm. Small enough for an
# engineering smoke per the M3/M5 doctrine.

set -euo pipefail

cd "$(dirname "$0")/.."

OV6T_KEEP_RATE=0.50 \
OV6T_LAYER=2 \
OV6T_N_ITEMS=10 \
OV6T_OUT_DIR="research/experiments/2026/artifacts/phase1_51V_ov6_tomato_motion_kr050_l2_smoke" \
  bash scripts/run_ov6_qwen_tomato_replication.sh
