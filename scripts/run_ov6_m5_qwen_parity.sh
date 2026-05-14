#!/usr/bin/env bash
# M5 OV-6 Qwen N=57 parity / timing confirmation.
#
# Hypothesis: the M3 Qwen kr=0.7/layer=2 codec_novel_coded point-estimate
# ordering is hardware-stable when score extraction is moved to precomputed
# sidecars. This is a focused confirmation, not an open sweep.

set -euo pipefail
LAST_ARM=""
trap 'echo "[m5-qwen-parity] arm $LAST_ARM failed at $(date -u +%Y-%m-%dT%H:%M:%SZ)"' ERR

cd "$(dirname "$0")/.."

PY="${M5Q_PYTHON:-./.venv/bin/python}"
MODEL_PATH="${M5Q_MODEL_PATH:-$HOME/models/Qwen2.5-VL-7B-Instruct-4bit}"
MANIFEST="${M5Q_MANIFEST:-research/benchmark_manifests/videomme_short_present_v1_n57.toml}"
OUT_DIR="${M5Q_OUT_DIR:-research/experiments/2026/artifacts/m5_ov6_qwen_n57_kr070_l2_parity}"
SIDECAR_DIR="${M5Q_SIDECAR_DIR:-$OUT_DIR/codec_score_sidecars}"
SIDECAR_MANIFEST="${M5Q_SIDECAR_MANIFEST:-$OUT_DIR/sidecar_manifest.json}"
EQUIV_ROOT="${M5Q_EQUIV_ROOT:-research/experiments/2026/artifacts/phase1_51V_ov6_sidecar_equivalence}"
FRAME_COUNT="${M5Q_FRAME_COUNT:-8}"
MAX_TOKENS="${M5Q_MAX_TOKENS:-32}"
LAYER="${M5Q_LAYER:-2}"
KEEP_RATE="${M5Q_KEEP_RATE:-0.70}"
SOURCES=(novel_coded motion residual)

mkdir -p "$OUT_DIR"

"${PY}" scripts/validate_ov6_sidecar_equivalence_gate.py \
  --root "$EQUIV_ROOT" \
  --geometry qwen_merged_groups_v1 \
  --frame-count "$FRAME_COUNT" \
  --sources "${SOURCES[@]}" \
  --allow-historical-commit

if [[ ! -f "$SIDECAR_MANIFEST" ]]; then
  "${PY}" scripts/build_ov6_codec_score_sidecars.py \
    --manifest "$MANIFEST" \
    --out-dir "$SIDECAR_DIR" \
    --manifest-json "$SIDECAR_MANIFEST" \
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
  --sources "${SOURCES[@]}"

validate_arm() {
  local label="$1"
  shift 1
  local arm_dir="$OUT_DIR/$label"
  local -a extra_validate_args=()
  if [[ "$label" == codec_* ]]; then
    extra_validate_args+=(--codec-score-sidecar-geometry qwen_merged_groups_v1)
  fi
  "${PY}" scripts/validate_track_b_arm_artifact.py \
    --arm-dir "$arm_dir" \
    --manifest "$MANIFEST" \
    --model-path "$MODEL_PATH" \
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
      echo "[m5-qwen-parity] === arm=$label SKIP (validated existing artifact) ==="
      return 0
    fi
    echo "[m5-qwen-parity] === arm=$label existing artifact failed validation ===" >&2
    return 1
  fi
  mkdir -p "$arm_dir"
  LAST_ARM="$label"
  echo "[m5-qwen-parity] === arm=$label starting $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  "${PY}" scripts/run_phase1_51V.py \
    --manifest "$MANIFEST" \
    --model-path "$MODEL_PATH" \
    --frame-count "$FRAME_COUNT" \
    --max-tokens "$MAX_TOKENS" \
    --output "$arm_dir/results.jsonl" \
    --summary "$arm_dir/summary.json" \
    "$@" \
    2>&1 | tee "$arm_dir/run.log"
  validate_arm "$label" "$@"
  echo "[m5-qwen-parity] === arm=$label done $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
}

run_arm dense --vision-tower-keep-rate 1.0
run_arm magnitude_norm \
  --vision-tower-layer "$LAYER" --vision-tower-keep-rate "$KEEP_RATE" \
  --score-mode magnitude_norm
run_arm uniform_random \
  --vision-tower-layer "$LAYER" --vision-tower-keep-rate "$KEEP_RATE" \
  --score-mode uniform_random --score-seed 42
for source in "${SOURCES[@]}"; do
  run_arm "codec_${source}" \
    --vision-tower-layer "$LAYER" --vision-tower-keep-rate "$KEEP_RATE" \
    --score-mode codec_grid --codec-score-source "$source" \
    --codec-score-sidecar-dir "$SIDECAR_DIR"
done

"${PY}" scripts/analyze_track_b_arm_set.py --root "$OUT_DIR"
