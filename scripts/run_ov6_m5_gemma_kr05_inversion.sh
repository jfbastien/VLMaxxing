#!/usr/bin/env bash
# M5 OV-6 Gemma kr=0.5/layer=2 random>magnitude cross-family replication.
#
# Hypothesis: the Phase-1 Qwen finding -- uniform_random beats magnitude_norm
# on 4/4 seeds at kr=0.5/layer=2/N=57 VideoMME-short -- also reproduces on
# Gemma 4 E4B + SigLIP at the same operating point. If it does, the
# "magnitude is a bad default at this operating cell" claim widens to a
# vision-tower-family-agnostic finding. If it does not, the claim narrows
# to Qwen ViT specifically and the paper must say so.
#
# This run uses no codec arms; the M3 sidecar-equivalence gate is not
# required. We compare magnitude_norm against uniform_random across the
# same four seeds Phase 1 used on Qwen: {1, 7, 42, 100}.
#
# Preregistered gate (analysis-side): >=3/4 seeds satisfy
#   uniform_random_accuracy >= magnitude_norm_accuracy (point estimate).
# Preregistered falsifier: any seed where magnitude beats random by
# >=3 items, OR <=1/4 seeds satisfy the gate.

set -euo pipefail
LAST_ARM=""
trap 'echo "[m5-gemma-kr05] arm $LAST_ARM failed at $(date -u +%Y-%m-%dT%H:%M:%SZ)"' ERR

cd "$(dirname "$0")/.."

PY="${M5GR_PYTHON:-./.venv/bin/python}"
MODEL_PATH="${M5GR_MODEL_PATH:-$HOME/models/gemma-4-e4b-it-4bit}"
MANIFEST="${M5GR_MANIFEST:-research/benchmark_manifests/videomme_short_present_v1_n57.toml}"
OUT_DIR="${M5GR_OUT_DIR:-research/experiments/2026/artifacts/m5_ov6_gemma_n57_kr050_l2_random_multiseed}"
FRAME_COUNT="${M5GR_FRAME_COUNT:-8}"
MAX_TOKENS="${M5GR_MAX_TOKENS:-32}"
LAYER="${M5GR_LAYER:-2}"
KEEP_RATE="${M5GR_KEEP_RATE:-0.50}"
RSS_GUARD_MB="${M5GR_RSS_GUARD_MB:-110000}"
MAX_PARSE_FAILURES="${M5GR_MAX_PARSE_FAILURES:-3}"
SEEDS=(${M5GR_SEEDS:-1 7 42 100})

mkdir -p "$OUT_DIR"

validate_arm() {
  local label="$1"
  shift 1
  local arm_dir="$OUT_DIR/$label"
  "${PY}" scripts/validate_track_b_arm_artifact.py \
    --arm-dir "$arm_dir" \
    --manifest "$MANIFEST" \
    --model-path "$MODEL_PATH" \
    --frame-count "$FRAME_COUNT" \
    --max-tokens "$MAX_TOKENS" \
    --allow-parse-failures --max-parse-failures "$MAX_PARSE_FAILURES" \
    "$@"
}

run_arm() {
  local label="$1"
  shift 1
  local arm_dir="$OUT_DIR/$label"
  if [[ -f "$arm_dir/summary.json" || -f "$arm_dir/results.jsonl" ]]; then
    if validate_arm "$label" "$@" >/dev/null; then
      echo "[m5-gemma-kr05] === arm=$label SKIP (validated existing artifact) ==="
      return 0
    fi
    echo "[m5-gemma-kr05] === arm=$label existing artifact failed validation ===" >&2
    return 1
  fi
  mkdir -p "$arm_dir"
  LAST_ARM="$label"
  echo "[m5-gemma-kr05] === arm=$label starting $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  "${PY}" scripts/run_phase1_63G_gemma_track_b.py \
    --manifest "$MANIFEST" \
    --model-path "$MODEL_PATH" \
    --frame-count "$FRAME_COUNT" \
    --max-tokens "$MAX_TOKENS" \
    --rss-guard-mb "$RSS_GUARD_MB" \
    --output "$arm_dir/results.jsonl" \
    --summary "$arm_dir/summary.json" \
    "$@" \
    2>&1 | tee "$arm_dir/run.log"
  validate_arm "$label" "$@"
  echo "[m5-gemma-kr05] === arm=$label done $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
}

echo "[m5-gemma-kr05] manifest=$MANIFEST keep_rate=$KEEP_RATE layer=$LAYER seeds=${SEEDS[*]}"

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

"${PY}" scripts/analyze_ov6_qwen_random_multiseed.py --root "$OUT_DIR" --label "Gemma"
