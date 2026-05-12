#!/usr/bin/env bash
# OV-6 Qwen random-baseline multi-seed check.
#
# Hypothesis: the kr=0.5/layer=2 uniform_random > magnitude_norm point-estimate
# inversion is not a seed-42 artifact. The analysis gate is in
# scripts/analyze_ov6_qwen_random_multiseed.py.

set -euo pipefail
LAST_ARM=""
trap 'echo "[ov6-random] arm $LAST_ARM failed at $(date -u +%Y-%m-%dT%H:%M:%SZ)"' ERR

cd "$(dirname "$0")/.."

PY="${OV6R_PYTHON:-uv run python}"
MODEL_PATH="${OV6R_MODEL_PATH:-$HOME/models/Qwen2.5-VL-7B-Instruct-4bit}"
MANIFEST="${OV6R_MANIFEST:-research/benchmark_manifests/videomme_short_present_v1_n57.toml}"
OUT_DIR="${OV6R_OUT_DIR:-research/experiments/2026/artifacts/phase1_51V_ov6_random_multiseed}"
FRAME_COUNT="${OV6R_FRAME_COUNT:-8}"
MAX_TOKENS="${OV6R_MAX_TOKENS:-32}"
LAYER="${OV6R_LAYER:-2}"
KEEP_RATE="${OV6R_KEEP_RATE:-0.50}"
SEEDS=(${OV6R_SEEDS:-1 7 42 100})

mkdir -p "$OUT_DIR"

run_arm() {
  local label="$1"
  shift 1
  local arm_dir="$OUT_DIR/$label"
  if [[ -f "$arm_dir/summary.json" ]]; then
    echo "[ov6-random] === arm=$label SKIP (already done) ==="
    return 0
  fi
  mkdir -p "$arm_dir"
  LAST_ARM="$label"
  echo "[ov6-random] === arm=$label starting $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  ${PY} scripts/run_phase1_51V.py \
    --manifest "$MANIFEST" \
    --model-path "$MODEL_PATH" \
    --frame-count "$FRAME_COUNT" \
    --max-tokens "$MAX_TOKENS" \
    --output "$arm_dir/results.jsonl" \
    --summary "$arm_dir/summary.json" \
    --allow-dirty \
    "$@" \
    2>&1 | tee "$arm_dir/run.log"
  echo "[ov6-random] === arm=$label done $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
}

echo "[ov6-random] manifest=$MANIFEST keep_rate=$KEEP_RATE layer=$LAYER seeds=${SEEDS[*]}"

run_arm magnitude_norm \
  --vision-tower-layer "$LAYER" \
  --vision-tower-keep-rate "$KEEP_RATE" \
  --score-mode magnitude_norm

for seed in "${SEEDS[@]}"; do
  run_arm "uniform_random_seed${seed}" \
    --vision-tower-layer "$LAYER" \
    --vision-tower-keep-rate "$KEEP_RATE" \
    --score-mode uniform_random \
    --score-seed "$seed"
done

${PY} scripts/analyze_ov6_qwen_random_multiseed.py --root "$OUT_DIR"
