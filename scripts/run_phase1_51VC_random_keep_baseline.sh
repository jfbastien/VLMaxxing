#!/usr/bin/env bash
# Phase 1.51VC competitor-positioning baseline:
# uniform_random keep at matched (L=2, kr=0.5) on the same Qwen 7B 8f
# VideoMME dev30 cell as Phase 1.51V Qwen cross-arch. The result is paired
# against the existing magnitude_norm baseline at fixed corpus, fixed dense
# reference, and fixed keep-rate.
#
# Usage:
#   bash scripts/run_phase1_51VC_random_keep_baseline.sh
set -euo pipefail
cd "$(dirname "$0")/.."

OUT="${PHASE1_51VC_OUT_DIR:-research/experiments/2026/artifacts/phase1_51VC_random_keep_baseline}"
mkdir -p "$OUT"

PY="${PYTHON:-./.venv/bin/python}"
DRIVER="scripts/run_phase1_51V.py"
MANIFEST="${PHASE1_51VC_MANIFEST:-research/benchmark_manifests/videomme_dev_v1.toml}"
N_ITEMS="${PHASE1_51VC_N_ITEMS:-0}"
FRAME_COUNT="${PHASE1_51VC_FRAME_COUNT:-8}"
MAX_TOKENS="${PHASE1_51VC_MAX_TOKENS:-32}"
MODEL_PATH="${PHASE1_51VC_MODEL_PATH:-$HOME/models/Qwen2.5-VL-7B-Instruct-4bit}"
RSS_GUARD_MB="${PHASE1_51VC_RSS_GUARD_MB:-10000}"
VISION_TOWER_LAYER="${PHASE1_51VC_VISION_TOWER_LAYER:-2}"
VISION_TOWER_KEEP_RATE="${PHASE1_51VC_VISION_TOWER_KEEP_RATE:-0.50}"
SCORE_SEED="${PHASE1_51VC_SCORE_SEED:-42}"

echo "[1.51VC] uniform_random arm at L=$VISION_TOWER_LAYER kr=$VISION_TOWER_KEEP_RATE seed=$SCORE_SEED"
"$PY" "$DRIVER" \
  --manifest "$MANIFEST" \
  --n-items "$N_ITEMS" \
  --frame-count "$FRAME_COUNT" \
  --max-tokens "$MAX_TOKENS" \
  --model-path "$MODEL_PATH" \
  --rss-guard-mb "$RSS_GUARD_MB" \
  --output "$OUT/videomme_dev30_${FRAME_COUNT}f_L${VISION_TOWER_LAYER}_kr050_uniform_random_seed${SCORE_SEED}.jsonl" \
  --summary "$OUT/videomme_dev30_${FRAME_COUNT}f_L${VISION_TOWER_LAYER}_kr050_uniform_random_seed${SCORE_SEED}_summary.json" \
  --allow-dirty \
  --vision-tower-layer "$VISION_TOWER_LAYER" \
  --vision-tower-keep-rate "$VISION_TOWER_KEEP_RATE" \
  --score-mode uniform_random \
  --score-seed "$SCORE_SEED"

echo "[1.51VC] done; positioning table will be built post-hoc by"
echo "         scripts/build_competitor_positioning_table.py"
