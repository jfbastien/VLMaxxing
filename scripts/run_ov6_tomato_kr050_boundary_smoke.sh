#!/usr/bin/env bash
# M3 OV-6 TOMATO motion kr=0.5/layer=2/N=10 aggressive-prune control.
#
# Phase 3 observed that at kr=0.7/layer=2/frame=8 on TOMATO motion N=30, every
# prune scheme collapses near the chance floor (dense 0.267 -> magnitude 0.133,
# codec_novel_coded 0.167).
#
# kr=0.5 keeps fewer groups than kr=0.7, so this script is not a clean
# prune-rate-vs-frame-budget discriminator. It is retained only as an optional
# aggressive-prune negative control. Use
# scripts/run_ov6_tomato_kr090_boundary_smoke.sh for the actual boundary smoke.

set -euo pipefail

cd "$(dirname "$0")/.."

OV6T_KEEP_RATE=0.50 \
OV6T_LAYER=2 \
OV6T_N_ITEMS=10 \
OV6T_OUT_DIR="research/experiments/2026/artifacts/phase1_51V_ov6_tomato_motion_kr050_l2_smoke" \
  bash scripts/run_ov6_qwen_tomato_replication.sh
