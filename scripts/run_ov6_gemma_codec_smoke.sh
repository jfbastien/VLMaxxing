#!/usr/bin/env bash
# OV-6 Gemma codec-grid smoke.
#
# CPU wiring must pass before this GPU job runs. The smoke intentionally uses a
# short N so geometry/provenance issues fail quickly before any broad Gemma run.

set -euo pipefail
LAST_ARM=""
trap 'echo "[ov6-gemma] arm $LAST_ARM failed at $(date -u +%Y-%m-%dT%H:%M:%SZ)"' ERR

cd "$(dirname "$0")/.."

PY="${OV6G_PYTHON:-./.venv/bin/python}"
MODEL_PATH="${OV6G_MODEL_PATH:-$HOME/models/gemma-4-e4b-it-4bit}"
MANIFEST="${OV6G_MANIFEST:-research/benchmark_manifests/videomme_dev_v1_short_only.toml}"
OUT_DIR="${OV6G_OUT_DIR:-research/experiments/2026/artifacts/phase1_63G_ov6_gemma_codec_smoke}"
SIDECAR_DIR="${OV6G_CODEC_SCORE_SIDECAR_DIR:-}"
SIDECAR_MANIFEST="${OV6G_CODEC_SCORE_SIDECAR_MANIFEST:-}"
N_ITEMS="${OV6G_N_ITEMS:-10}"
FRAME_COUNT="${OV6G_FRAME_COUNT:-8}"
MAX_TOKENS="${OV6G_MAX_TOKENS:-32}"
KEEP_RATE="${OV6G_KEEP_RATE:-0.70}"
LAYER="${OV6G_LAYER:-2}"
RSS_GUARD_MB="${RSS_GUARD_MB:-9000}"
MAX_PARSE_FAILURES="${OV6G_MAX_PARSE_FAILURES:-1}"

mkdir -p "$OUT_DIR"

if [[ -n "$SIDECAR_DIR" ]]; then
  if [[ -z "$SIDECAR_MANIFEST" ]]; then
    SIDECAR_MANIFEST="$(dirname "$SIDECAR_DIR")/sidecar_manifest.json"
  fi
  "${PY}" scripts/validate_ov6_codec_score_sidecars.py \
    --manifest-json "$SIDECAR_MANIFEST" \
    --sidecar-dir "$SIDECAR_DIR" \
    --input-manifest "$MANIFEST" \
    --geometry gemma_prepool_patches_v1 \
    --frame-count "$FRAME_COUNT" \
    --n-items "$N_ITEMS" \
    --sources novel_coded motion residual
fi

validate_arm() {
  local label="$1"
  shift 1
  local arm_dir="$OUT_DIR/$label"
  local -a extra_validate_args=(--allow-parse-failures --max-parse-failures "$MAX_PARSE_FAILURES")
  if [[ -n "$SIDECAR_DIR" && "$label" == codec_* ]]; then
    extra_validate_args+=(
      --codec-score-sidecar-dir "$SIDECAR_DIR"
      --codec-score-sidecar-geometry gemma_prepool_patches_v1
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
      echo "[ov6-gemma] === arm=$label SKIP (validated existing artifact) ==="
      return 0
    fi
    echo "[ov6-gemma] === arm=$label existing artifact failed validation ===" >&2
    return 1
  fi
  mkdir -p "$arm_dir"
  EXTRA_RUN_ARGS=()
  if [[ -n "$SIDECAR_DIR" && "$label" == codec_* ]]; then
    EXTRA_RUN_ARGS+=(--codec-score-sidecar-dir "$SIDECAR_DIR")
  fi
  LAST_ARM="$label"
  echo "[ov6-gemma] === arm=$label starting $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  "${PY}" scripts/run_phase1_63G_gemma_track_b.py \
    --manifest "$MANIFEST" \
    --n-items "$N_ITEMS" \
    --frame-count "$FRAME_COUNT" \
    --max-tokens "$MAX_TOKENS" \
    --model-path "$MODEL_PATH" \
    --rss-guard-mb "$RSS_GUARD_MB" \
    --output "$arm_dir/results.jsonl" \
    --summary "$arm_dir/summary.json" \
    "${EXTRA_RUN_ARGS[@]}" \
    "$@" \
    2>&1 | tee "$arm_dir/run.log"
  validate_arm "$label" "$@"
  echo "[ov6-gemma] === arm=$label done $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
}

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

"${PY}" scripts/analyze_track_b_arm_set.py --root "$OUT_DIR"
