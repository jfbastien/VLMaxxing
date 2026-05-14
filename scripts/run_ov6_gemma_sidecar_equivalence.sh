#!/usr/bin/env bash
# OV-6 Gemma sidecar equivalence gate.
#
# Hypothesis: precomputed Gemma pre-pool H.264 score sidecars preserve live-PyAV
# codec-grid behavior before any Gemma M5 N=57 confirmation uses sidecars.

set -euo pipefail
LAST_ARM=""
trap 'echo "[ov6-gemma-sidecar-eq] arm $LAST_ARM failed at $(date -u +%Y-%m-%dT%H:%M:%SZ)"' ERR

cd "$(dirname "$0")/.."

PY="${OV6GS_PYTHON:-./.venv/bin/python}"
MODEL_PATH="${OV6GS_MODEL_PATH:-$HOME/models/gemma-4-e4b-it-4bit}"
MANIFEST="${OV6GS_MANIFEST:-research/benchmark_manifests/videomme_dev_v1_short_only.toml}"
OUT_DIR="${OV6GS_OUT_DIR:-research/experiments/2026/artifacts/phase1_63G_ov6_gemma_sidecar_equivalence}"
SIDECAR_DIR="${OV6GS_SIDECAR_DIR:-$OUT_DIR/codec_score_sidecars}"
SIDECAR_MANIFEST="${OV6GS_SIDECAR_MANIFEST:-$OUT_DIR/sidecar_manifest.json}"
N_ITEMS="${OV6GS_N_ITEMS:-3}"
FRAME_COUNT="${OV6GS_FRAME_COUNT:-8}"
MAX_TOKENS="${OV6GS_MAX_TOKENS:-32}"
LAYER="${OV6GS_LAYER:-2}"
KEEP_RATE="${OV6GS_KEEP_RATE:-0.70}"
RSS_GUARD_MB="${OV6GS_RSS_GUARD_MB:-9000}"
MAX_PARSE_FAILURES="${OV6GS_MAX_PARSE_FAILURES:-1}"
SOURCES=(${OV6GS_SOURCES:-novel_coded motion residual})

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
  echo "[ov6-gemma-sidecar-eq] building sidecars: $SIDECAR_DIR"
  "${PY}" scripts/build_ov6_codec_score_sidecars.py \
    --manifest "$MANIFEST" \
    --out-dir "$SIDECAR_DIR" \
    --manifest-json "$SIDECAR_MANIFEST" \
    --n-items "$N_ITEMS" \
    --frame-count "$FRAME_COUNT" \
    --geometry gemma_prepool_patches_v1 \
    --sources "${SOURCES[@]}"
fi

"${PY}" scripts/validate_ov6_codec_score_sidecars.py \
  --manifest-json "$SIDECAR_MANIFEST" \
  --sidecar-dir "$SIDECAR_DIR" \
  --input-manifest "$MANIFEST" \
  --geometry gemma_prepool_patches_v1 \
  --frame-count "$FRAME_COUNT" \
  --n-items "$N_ITEMS" \
  --sources "${SOURCES[@]}" \
  --allow-dirty

commit_path "exp(ov6): gemma sidecar build for $OUT_DIR" "$OUT_DIR"

validate_arm() {
  local label="$1"
  shift 1
  local arm_dir="$OUT_DIR/$label"
  local -a extra_validate_args=(
    --allow-parse-failures
    --max-parse-failures "$MAX_PARSE_FAILURES"
  )
  if [[ "$label" == sidecar_* ]]; then
    extra_validate_args+=(
      --codec-score-sidecar-geometry gemma_prepool_patches_v1
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
      echo "[ov6-gemma-sidecar-eq] === arm=$label SKIP (validated existing artifact) ==="
      return 0
    fi
    echo "[ov6-gemma-sidecar-eq] === arm=$label existing artifact failed validation ===" >&2
    return 1
  fi
  mkdir -p "$arm_dir"
  LAST_ARM="$label"
  echo "[ov6-gemma-sidecar-eq] === arm=$label starting $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  "${PY}" scripts/run_phase1_63G_gemma_track_b.py \
    --manifest "$MANIFEST" \
    --n-items "$N_ITEMS" \
    --model-path "$MODEL_PATH" \
    --frame-count "$FRAME_COUNT" \
    --max-tokens "$MAX_TOKENS" \
    --rss-guard-mb "$RSS_GUARD_MB" \
    --output "$arm_dir/results.jsonl" \
    --summary "$arm_dir/summary.json" \
    --allow-dirty \
    "$@" \
    2>&1 | tee "$arm_dir/run.log"
  validate_arm "$label" "$@"
  commit_path "exp(ov6): gemma-sidecar-eq arm=$label" "$arm_dir"
  echo "[ov6-gemma-sidecar-eq] === arm=$label done $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
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

commit_path "exp(ov6): gemma-sidecar-eq analysis for $OUT_DIR" "$OUT_DIR"
