#!/usr/bin/env bash
# OV-6 sidecar equivalence gate.
#
# Hypothesis: precomputed H.264 score sidecars preserve live-PyAV codec-grid
# behavior while moving metadata extraction out of model-run timing.
#
# Gate: for each source, sidecar and live arms have zero choice/correctness and
# kept-count drift; sidecar load is <1s/item and lower than live extraction.

set -euo pipefail
LAST_ARM=""
trap 'echo "[ov6-sidecar-eq] arm $LAST_ARM failed at $(date -u +%Y-%m-%dT%H:%M:%SZ)"' ERR

cd "$(dirname "$0")/.."

PY="${OV6S_PYTHON:-./.venv/bin/python}"
MODEL_PATH="${OV6S_MODEL_PATH:-$HOME/models/Qwen2.5-VL-7B-Instruct-4bit}"
MANIFEST="${OV6S_MANIFEST:-research/benchmark_manifests/videomme_dev_v1_short_only.toml}"
N_ITEMS="${OV6S_N_ITEMS:-3}"
FRAME_COUNT="${OV6S_FRAME_COUNT:-8}"
DEFAULT_OUT_DIR="research/experiments/2026/artifacts/phase1_51V_ov6_sidecar_equivalence"
if [[ "$FRAME_COUNT" != "8" ]]; then
  DEFAULT_OUT_DIR="${DEFAULT_OUT_DIR}_f${FRAME_COUNT}"
fi
OUT_DIR="${OV6S_OUT_DIR:-$DEFAULT_OUT_DIR}"
SIDECAR_DIR="${OV6S_SIDECAR_DIR:-$OUT_DIR/codec_score_sidecars}"
SIDECAR_MANIFEST="${OV6S_SIDECAR_MANIFEST:-$OUT_DIR/sidecar_manifest.json}"
MAX_TOKENS="${OV6S_MAX_TOKENS:-32}"
LAYER="${OV6S_LAYER:-2}"
KEEP_RATE="${OV6S_KEEP_RATE:-0.70}"
SOURCES=(${OV6S_SOURCES:-novel_coded motion residual})

mkdir -p "$OUT_DIR"

commit_path() {
  local message="$1"
  shift
  local has_changes="no"
  for p in "$@"; do
    if [[ -n "$(git status --porcelain -- "$p")" ]]; then
      has_changes="yes"
      git add -- "$p"
    fi
  done
  if [[ "$has_changes" == "yes" ]]; then
    git commit -m "$message" >/dev/null
  fi
}

if [[ ! -f "$SIDECAR_MANIFEST" ]]; then
  echo "[ov6-sidecar-eq] building sidecars: $SIDECAR_DIR"
  "${PY}" scripts/build_ov6_codec_score_sidecars.py \
    --manifest "$MANIFEST" \
    --out-dir "$SIDECAR_DIR" \
    --manifest-json "$SIDECAR_MANIFEST" \
    --n-items "$N_ITEMS" \
    --frame-count "$FRAME_COUNT" \
    --geometry qwen_merged_groups_v1 \
    --sources "${SOURCES[@]}"
fi

"${PY}" scripts/validate_ov6_codec_score_sidecars.py \
  --manifest-json "$SIDECAR_MANIFEST" \
  --sidecar-dir "$SIDECAR_DIR" \
  --input-manifest "$MANIFEST" \
  --geometry qwen_merged_groups_v1 \
  --frame-count "$FRAME_COUNT" \
  --n-items "$N_ITEMS" \
  --sources "${SOURCES[@]}" \
  --allow-dirty

commit_path "exp(ov6): qwen sidecar build for $OUT_DIR" "$OUT_DIR"

validate_arm() {
  local label="$1"
  shift 1
  local arm_dir="$OUT_DIR/$label"
  local -a extra_validate_args=()
  if [[ "$label" == sidecar_* ]]; then
    extra_validate_args+=(
      --codec-score-sidecar-geometry qwen_merged_groups_v1
      --allow-dirty-artifact
    )
  fi
  "${PY}" scripts/validate_track_b_arm_artifact.py \
    --arm-dir "$arm_dir" \
    --manifest "$MANIFEST" \
    --model-path "$MODEL_PATH" \
    --n-items "$N_ITEMS" \
    --frame-count "$FRAME_COUNT" \
    --max-tokens "$MAX_TOKENS" \
    "${extra_validate_args[@]}" \
    "$@"
}

run_arm() {
  local label="$1"
  shift 1
  local arm_dir="$OUT_DIR/$label"
  if [[ -f "$arm_dir/summary.json" || -f "$arm_dir/results.jsonl" ]]; then
    if validate_arm "$label" "$@" >/dev/null; then
      echo "[ov6-sidecar-eq] === arm=$label SKIP (validated existing artifact) ==="
      return 0
    fi
    echo "[ov6-sidecar-eq] === arm=$label existing artifact failed validation ===" >&2
    return 1
  fi
  mkdir -p "$arm_dir"
  LAST_ARM="$label"
  echo "[ov6-sidecar-eq] === arm=$label starting $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  "${PY}" scripts/run_phase1_51V.py \
    --manifest "$MANIFEST" \
    --n-items "$N_ITEMS" \
    --model-path "$MODEL_PATH" \
    --frame-count "$FRAME_COUNT" \
    --max-tokens "$MAX_TOKENS" \
    --output "$arm_dir/results.jsonl" \
    --summary "$arm_dir/summary.json" \
    "$@" \
    2>&1 | tee "$arm_dir/run.log"
  validate_arm "$label" "$@"
  commit_path "exp(ov6): sidecar-eq arm=$label" "$arm_dir"
  echo "[ov6-sidecar-eq] === arm=$label done $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
}

for source in "${SOURCES[@]}"; do
  run_arm "live_${source}" \
    --vision-tower-layer "$LAYER" \
    --vision-tower-keep-rate "$KEEP_RATE" \
    --score-mode codec_grid \
    --codec-score-source "$source"

  run_arm "sidecar_${source}" \
    --vision-tower-layer "$LAYER" \
    --vision-tower-keep-rate "$KEEP_RATE" \
    --score-mode codec_grid \
    --codec-score-source "$source" \
    --codec-score-sidecar-dir "$SIDECAR_DIR"
done

"${PY}" scripts/analyze_ov6_sidecar_equivalence.py --root "$OUT_DIR" --sources "${SOURCES[@]}"

commit_path "exp(ov6): sidecar-eq analysis for $OUT_DIR" "$OUT_DIR"
