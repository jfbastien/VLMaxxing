#!/usr/bin/env bash
# M5 OV-6 Qwen kr=0.7 four-seed random-control protocol.
#
# Hypothesis: if codec_novel_coded is useful beyond exposing a weak
# magnitude_norm scorer, it should meet or exceed a same-run four-seed
# uniform-random keep distribution at Qwen VideoMME-short N=57, 8 frames,
# layer 2, keep-rate 0.7.

set -euo pipefail
LAST_ARM=""
trap 'echo "[m5-qwen-kr070-random-control] arm $LAST_ARM failed at $(date -u +%Y-%m-%dT%H:%M:%SZ)"' ERR

cd "$(dirname "$0")/.."

PY="${M5Q70_PYTHON:-./.venv/bin/python}"
MODEL_PATH="$HOME/models/Qwen2.5-VL-7B-Instruct-4bit"
MANIFEST="research/benchmark_manifests/videomme_short_present_v1_n57.toml"
CANONICAL_OUT_DIR="research/experiments/2026/artifacts/m5_ov6_qwen_n57_kr070_l2_random_control"
if [[ "${OV6_PREFLIGHT_ONLY:-0}" == "1" && -n "${OV6_CANONICAL_OUT_DIR_FOR_TESTS:-}" ]]; then
  CANONICAL_OUT_DIR="$OV6_CANONICAL_OUT_DIR_FOR_TESTS"
fi
OUT_DIR="${M5Q70_OUT_DIR:-$CANONICAL_OUT_DIR}"
SIDECAR_DIR="${M5Q70_SIDECAR_DIR:-$OUT_DIR/codec_score_sidecars}"
SIDECAR_MANIFEST="${M5Q70_SIDECAR_MANIFEST:-$OUT_DIR/sidecar_manifest.json}"
EQUIV_ROOT="research/experiments/2026/artifacts/phase1_51V_ov6_sidecar_equivalence"
FRAME_COUNT="8"
MAX_TOKENS="32"
LAYER="2"
KEEP_RATE="0.70"
SOURCE="novel_coded"
EQUIV_SOURCES=(novel_coded motion residual)
SEEDS=(1 7 42 100)
CLEAN_CONTROL_PREREG="${M5Q70_CLEAN_CONTROL_PREREG:-${M5Q_CLEAN_CONTROL_PREREG:-}}"
REGISTRY_PATH="research/experiments/registry.md"
WRAPPER_PATH="scripts/run_ov6_m5_qwen_kr070_random_control.sh"
RUN_MARKER="$OUT_DIR/clean_control_run_marker.json"
CONTROL_ROOT="m5_ov6_qwen_n57_kr070_l2_random_control"
COMPARATOR_PATHS=(
  "$CONTROL_ROOT/dense/"
  "$CONTROL_ROOT/magnitude_norm/"
  "$CONTROL_ROOT/codec_novel_coded/"
)
SEED_PATHS=(
  "$CONTROL_ROOT/uniform_random_seed1/"
  "$CONTROL_ROOT/uniform_random_seed7/"
  "$CONTROL_ROOT/uniform_random_seed42/"
  "$CONTROL_ROOT/uniform_random_seed100/"
)
AUDIT_FILENAME="codec_vs_random_multiseed_audit.json"

head_blob_exists() {
  local path="$1"
  local output
  if output="$(git cat-file -t "HEAD:$path" 2>&1)"; then
    if [[ "$output" == "blob" ]]; then
      return 0
    fi
    cat >&2 <<EOF
[m5-qwen-kr070-random-control] refusing to launch: HEAD:$path exists but is a
[m5-qwen-kr070-random-control] $output, not a committed file blob.
EOF
    exit 2
  fi
  case "$output" in
    *"does not exist in 'HEAD'"* | *"exists on disk, but not in 'HEAD'"* | *"Not a valid object name HEAD:"*)
      return 1
      ;;
  esac
  cat >&2 <<EOF
[m5-qwen-kr070-random-control] refusing to launch: git cat-file failed
[m5-qwen-kr070-random-control] unexpectedly while checking HEAD:$path:
$output
EOF
  exit 2
}

for forbidden_var in \
  M5Q70_MANIFEST \
  M5Q70_MODEL_PATH \
  M5Q70_FRAME_COUNT \
  M5Q70_MAX_TOKENS \
  M5Q70_LAYER \
  M5Q70_KEEP_RATE \
  M5Q70_EQUIV_ROOT \
  M5Q70_SIDECAR_DIR \
  M5Q70_SIDECAR_MANIFEST; do
  if [[ -n "${!forbidden_var:-}" ]]; then
    cat >&2 <<EOF
[m5-qwen-kr070-random-control] refusing to launch: $forbidden_var is not
[m5-qwen-kr070-random-control] allowed for the clean-control protocol. The
[m5-qwen-kr070-random-control] manifest, frame count, max tokens, layer,
[m5-qwen-kr070-random-control] keep rate, sidecar path, and sidecar-equivalence gate are
[m5-qwen-kr070-random-control] fixed by the preregistration.
EOF
    exit 2
  fi
done

out_dir_overridden=0
if [[ "$OUT_DIR" != "$CANONICAL_OUT_DIR" ]]; then
  out_dir_overridden=1
fi

clean_control_prereg_path_ok=0
clean_control_prereg_committed=0
clean_control_prereg_dirty=0
registry_dirty=0
clean_control_prereg_dir="${CLEAN_CONTROL_PREREG%/*}"
clean_control_prereg_name="${CLEAN_CONTROL_PREREG##*/}"
if [[ "$clean_control_prereg_dir" == "research/experiments/2026" ]] \
  && [[ "$clean_control_prereg_name" == *qwen*kr070*random*control*prereg.md ]]; then
  clean_control_prereg_path_ok=1
fi

if [[ -n "$CLEAN_CONTROL_PREREG" && "$clean_control_prereg_path_ok" == "1" ]]; then
  if ! git diff --quiet -- "$CLEAN_CONTROL_PREREG" \
    || ! git diff --cached --quiet -- "$CLEAN_CONTROL_PREREG"; then
    clean_control_prereg_dirty=1
  fi
fi

if head_blob_exists "$REGISTRY_PATH"; then
  if ! git diff --quiet -- "$REGISTRY_PATH" \
    || ! git diff --cached --quiet -- "$REGISTRY_PATH"; then
    registry_dirty=1
  fi
fi

if [[ -n "$CLEAN_CONTROL_PREREG" ]] \
  && [[ "$clean_control_prereg_path_ok" == "1" ]] \
  && head_blob_exists "$CLEAN_CONTROL_PREREG" \
  && git grep -q --fixed-strings "$WRAPPER_PATH" HEAD -- "$CLEAN_CONTROL_PREREG" \
  && git grep -q --fixed-strings "$CONTROL_ROOT" HEAD -- "$CLEAN_CONTROL_PREREG" \
  && git grep -q --fixed-strings "$CONTROL_ROOT/dense/" HEAD -- "$CLEAN_CONTROL_PREREG" \
  && git grep -q --fixed-strings "$CONTROL_ROOT/magnitude_norm/" HEAD -- "$CLEAN_CONTROL_PREREG" \
  && git grep -q --fixed-strings "$CONTROL_ROOT/codec_novel_coded/" HEAD -- "$CLEAN_CONTROL_PREREG" \
  && git grep -q --fixed-strings "$CONTROL_ROOT/uniform_random_seed1/" HEAD -- "$CLEAN_CONTROL_PREREG" \
  && git grep -q --fixed-strings "$CONTROL_ROOT/uniform_random_seed7/" HEAD -- "$CLEAN_CONTROL_PREREG" \
  && git grep -q --fixed-strings "$CONTROL_ROOT/uniform_random_seed42/" HEAD -- "$CLEAN_CONTROL_PREREG" \
  && git grep -q --fixed-strings "$CONTROL_ROOT/uniform_random_seed100/" HEAD -- "$CLEAN_CONTROL_PREREG" \
  && git grep -q --fixed-strings "$AUDIT_FILENAME" HEAD -- "$CLEAN_CONTROL_PREREG" \
  && head_blob_exists "$REGISTRY_PATH" \
  && git grep -q --fixed-strings "$CLEAN_CONTROL_PREREG" HEAD -- "$REGISTRY_PATH" \
  && git grep -q --fixed-strings "$WRAPPER_PATH" HEAD -- "$REGISTRY_PATH" \
  && git grep -q --fixed-strings "$CONTROL_ROOT/dense/" HEAD -- "$REGISTRY_PATH" \
  && git grep -q --fixed-strings "$CONTROL_ROOT/magnitude_norm/" HEAD -- "$REGISTRY_PATH" \
  && git grep -q --fixed-strings "$CONTROL_ROOT/codec_novel_coded/" HEAD -- "$REGISTRY_PATH" \
  && git grep -q --fixed-strings "$CONTROL_ROOT/uniform_random_seed1/" HEAD -- "$REGISTRY_PATH" \
  && git grep -q --fixed-strings "$CONTROL_ROOT/uniform_random_seed7/" HEAD -- "$REGISTRY_PATH" \
  && git grep -q --fixed-strings "$CONTROL_ROOT/uniform_random_seed42/" HEAD -- "$REGISTRY_PATH" \
  && git grep -q --fixed-strings "$CONTROL_ROOT/uniform_random_seed100/" HEAD -- "$REGISTRY_PATH" \
  && git grep -q --fixed-strings "$AUDIT_FILENAME" HEAD -- "$REGISTRY_PATH" \
  && git diff --quiet -- "$CLEAN_CONTROL_PREREG" \
  && git diff --cached --quiet -- "$CLEAN_CONTROL_PREREG" \
  && git diff --quiet -- "$REGISTRY_PATH" \
  && git diff --cached --quiet -- "$REGISTRY_PATH"; then
  clean_control_prereg_committed=1
fi

if [[ "$clean_control_prereg_dirty" == "1" ]]; then
  cat >&2 <<EOF
[m5-qwen-kr070-random-control] refusing to launch: clean-control preregistration
[m5-qwen-kr070-random-control] has staged or unstaged edits:
[m5-qwen-kr070-random-control]   $CLEAN_CONTROL_PREREG
[m5-qwen-kr070-random-control] Commit it before launch so the random-control
[m5-qwen-kr070-random-control] gate cannot be retrofitted after seeing results.
EOF
  exit 2
fi

if [[ "$clean_control_prereg_path_ok" == "1" && "$registry_dirty" == "1" ]]; then
  cat >&2 <<EOF
[m5-qwen-kr070-random-control] refusing to launch: experiment registry has
[m5-qwen-kr070-random-control] staged or unstaged edits:
[m5-qwen-kr070-random-control]   $REGISTRY_PATH
[m5-qwen-kr070-random-control] Commit the registry entry before launch.
EOF
  exit 2
fi

if [[ "$clean_control_prereg_committed" != "1" ]]; then
  cat >&2 <<EOF
[m5-qwen-kr070-random-control] refusing to launch: this clean-control protocol
[m5-qwen-kr070-random-control] requires a complete, committed preregistration and
[m5-qwen-kr070-random-control] registry entry before any random arm runs.
[m5-qwen-kr070-random-control] Required preregistration path pattern:
[m5-qwen-kr070-random-control]   research/experiments/2026/*qwen*kr070*random*control*prereg.md
[m5-qwen-kr070-random-control] The committed preregistration and registry must name:
[m5-qwen-kr070-random-control]   $WRAPPER_PATH
[m5-qwen-kr070-random-control]   $CONTROL_ROOT/dense/
[m5-qwen-kr070-random-control]   $CONTROL_ROOT/magnitude_norm/
[m5-qwen-kr070-random-control]   $CONTROL_ROOT/codec_novel_coded/
[m5-qwen-kr070-random-control]   $CONTROL_ROOT/uniform_random_seed1/
[m5-qwen-kr070-random-control]   $CONTROL_ROOT/uniform_random_seed7/
[m5-qwen-kr070-random-control]   $CONTROL_ROOT/uniform_random_seed42/
[m5-qwen-kr070-random-control]   $CONTROL_ROOT/uniform_random_seed100/
[m5-qwen-kr070-random-control]   $AUDIT_FILENAME
[m5-qwen-kr070-random-control] Launch with:
[m5-qwen-kr070-random-control]   M5Q_CLEAN_CONTROL_PREREG=<committed repo-relative preregistration path> $WRAPPER_PATH
EOF
  exit 2
fi

require_clean_except_output_root() {
  local -a status_args=(status --short -- .)
  local exclude_path
  if exclude_path="$(output_root_exclude_path)"; then
    status_args+=(":(exclude)$exclude_path")
  fi
  local status
  status="$(git "${status_args[@]}")"
  if [[ -n "$status" ]]; then
    cat >&2 <<EOF
[m5-qwen-kr070-random-control] refusing to launch: worktree has changes outside
[m5-qwen-kr070-random-control] the canonical output root. Commit, stash, or move
[m5-qwen-kr070-random-control] unrelated changes before running this experiment.
[m5-qwen-kr070-random-control] Allowed dirty root:
[m5-qwen-kr070-random-control]   $OUT_DIR
[m5-qwen-kr070-random-control] git status --short:
$status
EOF
    exit 2
  fi
}

output_root_exclude_path() {
  local repo_root
  repo_root="$(pwd -P)"
  if [[ "$OUT_DIR" == /* ]]; then
    case "$OUT_DIR" in
      "$repo_root"/*)
        printf "%s\n" "${OUT_DIR#$repo_root/}"
        return 0
        ;;
      *)
        return 1
        ;;
    esac
  fi
  printf "%s\n" "$OUT_DIR"
}

if [[ "$out_dir_overridden" == "1" ]]; then
  cat >&2 <<EOF
[m5-qwen-kr070-random-control] refusing to launch: output-root overrides are not
[m5-qwen-kr070-random-control] allowed for the clean-control protocol.
[m5-qwen-kr070-random-control] Canonical root:
[m5-qwen-kr070-random-control]   $CANONICAL_OUT_DIR
[m5-qwen-kr070-random-control] Requested root:
[m5-qwen-kr070-random-control]   $OUT_DIR
EOF
  exit 2
fi

require_clean_except_output_root

existing_protocol_artifact=0
for artifact_path in \
  "$OUT_DIR/dense" \
  "$OUT_DIR/magnitude_norm" \
  "$OUT_DIR/codec_novel_coded" \
  "$OUT_DIR/uniform_random_seed1" \
  "$OUT_DIR/uniform_random_seed7" \
  "$OUT_DIR/uniform_random_seed42" \
  "$OUT_DIR/uniform_random_seed100" \
  "$SIDECAR_DIR" \
  "$SIDECAR_MANIFEST" \
  "$OUT_DIR/$AUDIT_FILENAME"; do
  if [[ -e "$artifact_path" ]]; then
    existing_protocol_artifact=1
  fi
done

if [[ "$existing_protocol_artifact" == "1" && ! -f "$RUN_MARKER" ]]; then
  cat >&2 <<EOF
[m5-qwen-kr070-random-control] refusing to launch: canonical control artifacts
[m5-qwen-kr070-random-control] already exist but the wrapper marker is missing:
[m5-qwen-kr070-random-control]   $RUN_MARKER
[m5-qwen-kr070-random-control] Do not adopt ad-hoc generic-runner outputs into
[m5-qwen-kr070-random-control] the clean-control protocol. Move them aside or
[m5-qwen-kr070-random-control] record a post-hoc closure note instead.
EOF
  exit 2
fi

if [[ -f "$RUN_MARKER" ]]; then
  current_git_commit="$(git rev-parse HEAD)"
  for marker in \
    '"schema": "ov6_qwen_kr070_random_control_run_v1"' \
    "\"git_commit\": \"$current_git_commit\"" \
    "\"preregistration\": \"$CLEAN_CONTROL_PREREG\"" \
    "\"wrapper\": \"$WRAPPER_PATH\"" \
    "\"root\": \"$CONTROL_ROOT\"" \
    "\"manifest\": \"$MANIFEST\"" \
    '"model": "Qwen2.5-VL-7B-Instruct-4bit"' \
    "\"frame_count\": \"$FRAME_COUNT\"" \
    "\"layer\": \"$LAYER\"" \
    '"configured_keep_rate": "0.70"' \
    '"seeds": "1 7 42 100"'; do
    if ! grep -Fq "$marker" "$RUN_MARKER"; then
      cat >&2 <<EOF
[m5-qwen-kr070-random-control] refusing to resume: run marker does not match
[m5-qwen-kr070-random-control] the committed protocol marker '$marker':
[m5-qwen-kr070-random-control]   $RUN_MARKER
EOF
      exit 2
    fi
  done
fi

if [[ "${OV6_PREFLIGHT_ONLY:-0}" == "1" ]]; then
  echo "[m5-qwen-kr070-random-control] preflight passed"
  exit 0
fi

mkdir -p "$OUT_DIR"
if [[ ! -f "$RUN_MARKER" ]]; then
  git_commit="$(git rev-parse HEAD)"
  cat >"$RUN_MARKER" <<EOF
{
  "schema": "ov6_qwen_kr070_random_control_run_v1",
  "generated_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "git_commit": "$git_commit",
  "preregistration": "$CLEAN_CONTROL_PREREG",
  "wrapper": "$WRAPPER_PATH",
  "root": "$CONTROL_ROOT",
  "manifest": "$MANIFEST",
  "model": "Qwen2.5-VL-7B-Instruct-4bit",
  "frame_count": "$FRAME_COUNT",
  "layer": "$LAYER",
  "configured_keep_rate": "$KEEP_RATE",
  "seeds": "1 7 42 100"
}
EOF
fi

"${PY}" scripts/validate_ov6_sidecar_equivalence_gate.py \
  --root "$EQUIV_ROOT" \
  --geometry qwen_merged_groups_v1 \
  --frame-count "$FRAME_COUNT" \
  --sources "${EQUIV_SOURCES[@]}" \
  --allow-historical-commit

if [[ ! -f "$SIDECAR_MANIFEST" ]]; then
  "${PY}" scripts/build_ov6_codec_score_sidecars.py \
    --manifest "$MANIFEST" \
    --out-dir "$SIDECAR_DIR" \
    --manifest-json "$SIDECAR_MANIFEST" \
    --frame-count "$FRAME_COUNT" \
    --geometry qwen_merged_groups_v1 \
    --sources "$SOURCE"
fi

"${PY}" scripts/validate_ov6_codec_score_sidecars.py \
  --manifest-json "$SIDECAR_MANIFEST" \
  --sidecar-dir "$SIDECAR_DIR" \
  --input-manifest "$MANIFEST" \
  --geometry qwen_merged_groups_v1 \
  --frame-count "$FRAME_COUNT" \
  --sources "$SOURCE"

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
    if validate_arm "$label" "$@"; then
      echo "[m5-qwen-kr070-random-control] === arm=$label SKIP (validated existing artifact) ==="
      return 0
    fi
    echo "[m5-qwen-kr070-random-control] === arm=$label existing artifact failed validation ===" >&2
    return 1
  fi
  mkdir -p "$arm_dir"
  LAST_ARM="$label"
  echo "[m5-qwen-kr070-random-control] === arm=$label starting $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  "${PY}" scripts/run_phase1_51V.py \
    --manifest "$MANIFEST" \
    --model-path "$MODEL_PATH" \
    --frame-count "$FRAME_COUNT" \
    --max-tokens "$MAX_TOKENS" \
    --output "$arm_dir/results.jsonl" \
    --summary "$arm_dir/summary.json" \
    --allow-dirty \
    "$@" \
    2>&1 | tee "$arm_dir/run.log"
  validate_arm "$label" "$@"
  echo "[m5-qwen-kr070-random-control] === arm=$label done $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
}

echo "[m5-qwen-kr070-random-control] manifest=$MANIFEST keep_rate=$KEEP_RATE layer=$LAYER seeds=${SEEDS[*]}"

run_arm dense --vision-tower-keep-rate 1.0
run_arm magnitude_norm \
  --vision-tower-layer "$LAYER" --vision-tower-keep-rate "$KEEP_RATE" \
  --score-mode magnitude_norm
run_arm codec_novel_coded \
  --vision-tower-layer "$LAYER" --vision-tower-keep-rate "$KEEP_RATE" \
  --score-mode codec_grid --codec-score-source "$SOURCE" \
  --codec-score-sidecar-dir "$SIDECAR_DIR"
for seed in "${SEEDS[@]}"; do
  run_arm "uniform_random_seed${seed}" \
    --vision-tower-layer "$LAYER" --vision-tower-keep-rate "$KEEP_RATE" \
    --score-mode uniform_random \
    --score-seed "$seed"
done

"${PY}" scripts/analyze_ov6_qwen_kr070_random_control.py --root "$OUT_DIR"
