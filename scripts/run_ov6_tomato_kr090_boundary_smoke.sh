#!/usr/bin/env bash
# M3 OV-6 TOMATO motion kr=0.9/layer=2/N=9 boundary diagnostic smoke.
#
# Phase 3 found that TOMATO motion collapses near the sparse floor at
# kr=0.69/layer=2/frame=8 on N=30. This smoke tests the useful boundary
# question: does a milder prune recover signal on a balanced small slice, or is
# the failure mainly frame/content/model headroom?
#
# Hypothesis H_keep: if prune rate is the main boundary, kr=0.9 should lift at
# least one sparse arm toward dense on a balanced N=9 slice.
# Hypothesis H_content: if TOMATO motion is headroom/content limited at 8 frames,
# dense stays weak or all sparse arms remain near the previous sparse floor.
#
# Gate for follow-up: promote only if best sparse arm is within one item of dense
# and above the prior sparse-floor band (>0.22 on N=9). Otherwise keep TOMATO as
# a boundary diagnostic and do not spend M5 time on this branch.

set -euo pipefail

cd "$(dirname "$0")/.."

OV6T_MANIFEST="research/benchmark_manifests/tomato_motion_dev_v2_balanced_n9.toml" \
OV6T_KEEP_RATE=0.90 \
OV6T_LAYER=2 \
OV6T_N_ITEMS=0 \
OV6T_OUT_DIR="research/experiments/2026/artifacts/phase1_51V_ov6_tomato_motion_kr090_l2_balanced_smoke" \
  bash scripts/run_ov6_qwen_tomato_replication.sh
