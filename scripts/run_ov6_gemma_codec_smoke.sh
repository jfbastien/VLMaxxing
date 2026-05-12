#!/usr/bin/env bash
# OV-6 Gemma codec-grid smoke.
#
# CPU wiring must pass before this GPU job runs. The smoke intentionally uses a
# short N so geometry/provenance issues fail quickly before any broad Gemma run.

set -uo pipefail
trap 'echo "[ov6-gemma] arm $LAST_ARM failed at $(date -u +%Y-%m-%dT%H:%M:%SZ); continuing"' ERR

cd "$(dirname "$0")/.."

PY="${OV6G_PYTHON:-uv run python}"
MODEL_PATH="${OV6G_MODEL_PATH:-$HOME/models/gemma-4-e4b-it-4bit}"
MANIFEST="${OV6G_MANIFEST:-research/benchmark_manifests/videomme_dev_v1_short_only.toml}"
OUT_DIR="${OV6G_OUT_DIR:-research/experiments/2026/artifacts/phase1_63G_ov6_gemma_codec_smoke}"
N_ITEMS="${OV6G_N_ITEMS:-10}"
FRAME_COUNT="${OV6G_FRAME_COUNT:-8}"
KEEP_RATE="${OV6G_KEEP_RATE:-0.70}"
LAYER="${OV6G_LAYER:-2}"
RSS_GUARD_MB="${RSS_GUARD_MB:-9000}"

mkdir -p "$OUT_DIR"
LAST_ARM=""

run_arm() {
  local label="$1"
  shift 1
  local arm_dir="$OUT_DIR/$label"
  if [[ -f "$arm_dir/summary.json" ]]; then
    echo "[ov6-gemma] === arm=$label SKIP (already done) ==="
    return 0
  fi
  mkdir -p "$arm_dir"
  LAST_ARM="$label"
  echo "[ov6-gemma] === arm=$label starting $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  ${PY} scripts/run_phase1_63G_gemma_track_b.py \
    --manifest "$MANIFEST" \
    --n-items "$N_ITEMS" \
    --frame-count "$FRAME_COUNT" \
    --max-tokens 32 \
    --model-path "$MODEL_PATH" \
    --rss-guard-mb "$RSS_GUARD_MB" \
    --output "$arm_dir/results.jsonl" \
    --summary "$arm_dir/summary.json" \
    --allow-dirty \
    "$@" \
    2>&1 | tee "$arm_dir/run.log"
  echo "[ov6-gemma] === arm=$label done $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
}

run_arm dense \
  --vision-tower-keep-rate 1.0

run_arm magnitude_norm \
  --vision-tower-layer "$LAYER" \
  --vision-tower-keep-rate "$KEEP_RATE" \
  --score-mode magnitude_norm

run_arm codec_novel_coded \
  --vision-tower-layer "$LAYER" \
  --vision-tower-keep-rate "$KEEP_RATE" \
  --score-mode codec_grid \
  --codec-score-source novel_coded

run_arm codec_residual \
  --vision-tower-layer "$LAYER" \
  --vision-tower-keep-rate "$KEEP_RATE" \
  --score-mode codec_grid \
  --codec-score-source residual
