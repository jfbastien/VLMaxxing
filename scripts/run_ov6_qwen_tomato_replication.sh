#!/usr/bin/env bash
# OV-6 Qwen TOMATO motion replication.
#
# Hypothesis: if the kr=0.7/layer=2 codec_novel_coded point-estimate advantage
# is not VideoMME-short-specific, it should survive on TOMATO motion items.

set -euo pipefail
LAST_ARM=""
trap 'echo "[ov6-tomato] arm $LAST_ARM failed at $(date -u +%Y-%m-%dT%H:%M:%SZ)"' ERR

cd "$(dirname "$0")/.."

PY="${OV6T_PYTHON:-uv run python}"
MODEL_PATH="${OV6T_MODEL_PATH:-$HOME/models/Qwen2.5-VL-7B-Instruct-4bit}"
MANIFEST="${OV6T_MANIFEST:-research/benchmark_manifests/tomato_motion_dev_v2.toml}"
OUT_DIR="${OV6T_OUT_DIR:-research/experiments/2026/artifacts/phase1_51V_ov6_tomato_motion_kr070_l2}"
N_ITEMS="${OV6T_N_ITEMS:-0}"
FRAME_COUNT="${OV6T_FRAME_COUNT:-8}"
MAX_TOKENS="${OV6T_MAX_TOKENS:-32}"
LAYER="${OV6T_LAYER:-2}"
KEEP_RATE="${OV6T_KEEP_RATE:-0.70}"

mkdir -p "$OUT_DIR"

run_arm() {
  local label="$1"
  shift 1
  local arm_dir="$OUT_DIR/$label"
  if [[ -f "$arm_dir/summary.json" || -f "$arm_dir/results.jsonl" ]]; then
    if ${PY} scripts/validate_track_b_arm_artifact.py \
      --arm-dir "$arm_dir" \
      --manifest "$MANIFEST" \
      --model-path "$MODEL_PATH" \
      --n-items "$N_ITEMS" \
      --frame-count "$FRAME_COUNT" \
      --max-tokens "$MAX_TOKENS" \
      "$@" >/dev/null; then
      echo "[ov6-tomato] === arm=$label SKIP (validated existing artifact) ==="
      return 0
    fi
    echo "[ov6-tomato] === arm=$label existing artifact failed validation ===" >&2
    return 1
  fi
  mkdir -p "$arm_dir"
  LAST_ARM="$label"
  echo "[ov6-tomato] === arm=$label starting $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  ${PY} scripts/run_phase1_51V.py \
    --manifest "$MANIFEST" \
    --n-items "$N_ITEMS" \
    --model-path "$MODEL_PATH" \
    --frame-count "$FRAME_COUNT" \
    --max-tokens "$MAX_TOKENS" \
    --output "$arm_dir/results.jsonl" \
    --summary "$arm_dir/summary.json" \
    --allow-dirty \
    "$@" \
    2>&1 | tee "$arm_dir/run.log"
  echo "[ov6-tomato] === arm=$label done $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
}

echo "[ov6-tomato] manifest=$MANIFEST keep_rate=$KEEP_RATE layer=$LAYER n_items=$N_ITEMS"

run_arm dense \
  --vision-tower-keep-rate 1.0

run_arm magnitude_norm \
  --vision-tower-layer "$LAYER" \
  --vision-tower-keep-rate "$KEEP_RATE" \
  --score-mode magnitude_norm

run_arm uniform_random \
  --vision-tower-layer "$LAYER" \
  --vision-tower-keep-rate "$KEEP_RATE" \
  --score-mode uniform_random \
  --score-seed 42

run_arm codec_novel_coded \
  --vision-tower-layer "$LAYER" \
  --vision-tower-keep-rate "$KEEP_RATE" \
  --score-mode codec_grid \
  --codec-score-source novel_coded

run_arm codec_motion \
  --vision-tower-layer "$LAYER" \
  --vision-tower-keep-rate "$KEEP_RATE" \
  --score-mode codec_grid \
  --codec-score-source motion

run_arm codec_residual \
  --vision-tower-layer "$LAYER" \
  --vision-tower-keep-rate "$KEEP_RATE" \
  --score-mode codec_grid \
  --codec-score-source residual
