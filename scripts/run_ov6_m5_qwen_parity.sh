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
CANONICAL_OUT_DIR="research/experiments/2026/artifacts/m5_ov6_qwen_n57_kr070_l2_parity"
if [[ "${OV6_PREFLIGHT_ONLY:-0}" == "1" && -n "${OV6_CANONICAL_OUT_DIR_FOR_TESTS:-}" ]]; then
  CANONICAL_OUT_DIR="$OV6_CANONICAL_OUT_DIR_FOR_TESTS"
fi
OUT_DIR="${M5Q_OUT_DIR:-$CANONICAL_OUT_DIR}"
SIDECAR_DIR="${M5Q_SIDECAR_DIR:-$OUT_DIR/codec_score_sidecars}"
SIDECAR_MANIFEST="${M5Q_SIDECAR_MANIFEST:-$OUT_DIR/sidecar_manifest.json}"
EQUIV_ROOT="${M5Q_EQUIV_ROOT:-research/experiments/2026/artifacts/phase1_51V_ov6_sidecar_equivalence}"
FRAME_COUNT="${M5Q_FRAME_COUNT:-8}"
MAX_TOKENS="${M5Q_MAX_TOKENS:-32}"
LAYER="${M5Q_LAYER:-2}"
KEEP_RATE="${M5Q_KEEP_RATE:-0.70}"
SOURCES=(novel_coded motion residual)
CLEAN_CONTROL_PREREG="${M5Q_CLEAN_CONTROL_PREREG:-}"
ALLOW_CLOSE_RANDOM_CONTROL_WINDOW="${OV6_ALLOW_CLOSE_RANDOM_CONTROL_WINDOW:-0}"
CLOSURE_RECORD="${OV6_CLOSURE_RECORD:-}"
REGISTRY_PATH="research/experiments/registry.md"
out_dir_overridden=0
if [[ "${M5Q_OUT_DIR:-$CANONICAL_OUT_DIR}" != "$CANONICAL_OUT_DIR" ]]; then
  out_dir_overridden=1
fi

clean_control_prereg_committed=0
clean_control_prereg_path_ok=0
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

if [[ "$(git cat-file -t "HEAD:$REGISTRY_PATH" 2>/dev/null || true)" == "blob" ]]; then
  if ! git diff --quiet -- "$REGISTRY_PATH" \
    || ! git diff --cached --quiet -- "$REGISTRY_PATH"; then
    registry_dirty=1
  fi
fi

if [[ -n "$CLEAN_CONTROL_PREREG" ]] \
  && [[ "$clean_control_prereg_path_ok" == "1" ]] \
  && [[ "$(git cat-file -t "HEAD:$CLEAN_CONTROL_PREREG" 2>/dev/null || true)" == "blob" ]] \
  && git grep -q --fixed-strings "m5_ov6_qwen_n57_kr070_l2_random_control" HEAD -- "$CLEAN_CONTROL_PREREG" \
  && git grep -q --fixed-strings "m5_ov6_qwen_n57_kr070_l2_random_control/dense/" HEAD -- "$CLEAN_CONTROL_PREREG" \
  && git grep -q --fixed-strings "m5_ov6_qwen_n57_kr070_l2_random_control/magnitude_norm/" HEAD -- "$CLEAN_CONTROL_PREREG" \
  && git grep -q --fixed-strings "m5_ov6_qwen_n57_kr070_l2_random_control/codec_novel_coded/" HEAD -- "$CLEAN_CONTROL_PREREG" \
  && git grep -q --fixed-strings "m5_ov6_qwen_n57_kr070_l2_random_control/uniform_random_seed1/" HEAD -- "$CLEAN_CONTROL_PREREG" \
  && git grep -q --fixed-strings "m5_ov6_qwen_n57_kr070_l2_random_control/uniform_random_seed7/" HEAD -- "$CLEAN_CONTROL_PREREG" \
  && git grep -q --fixed-strings "m5_ov6_qwen_n57_kr070_l2_random_control/uniform_random_seed42/" HEAD -- "$CLEAN_CONTROL_PREREG" \
  && git grep -q --fixed-strings "m5_ov6_qwen_n57_kr070_l2_random_control/uniform_random_seed100/" HEAD -- "$CLEAN_CONTROL_PREREG" \
  && git grep -q --fixed-strings "codec_vs_random_multiseed_audit.json" HEAD -- "$CLEAN_CONTROL_PREREG" \
  && [[ "$(git cat-file -t "HEAD:$REGISTRY_PATH" 2>/dev/null || true)" == "blob" ]] \
  && git grep -q --fixed-strings "$CLEAN_CONTROL_PREREG" HEAD -- "$REGISTRY_PATH" \
  && git grep -q --fixed-strings "m5_ov6_qwen_n57_kr070_l2_random_control/dense/" HEAD -- "$REGISTRY_PATH" \
  && git grep -q --fixed-strings "m5_ov6_qwen_n57_kr070_l2_random_control/magnitude_norm/" HEAD -- "$REGISTRY_PATH" \
  && git grep -q --fixed-strings "m5_ov6_qwen_n57_kr070_l2_random_control/codec_novel_coded/" HEAD -- "$REGISTRY_PATH" \
  && git grep -q --fixed-strings "m5_ov6_qwen_n57_kr070_l2_random_control/uniform_random_seed1/" HEAD -- "$REGISTRY_PATH" \
  && git grep -q --fixed-strings "m5_ov6_qwen_n57_kr070_l2_random_control/uniform_random_seed7/" HEAD -- "$REGISTRY_PATH" \
  && git grep -q --fixed-strings "m5_ov6_qwen_n57_kr070_l2_random_control/uniform_random_seed42/" HEAD -- "$REGISTRY_PATH" \
  && git grep -q --fixed-strings "m5_ov6_qwen_n57_kr070_l2_random_control/uniform_random_seed100/" HEAD -- "$REGISTRY_PATH" \
  && git grep -q --fixed-strings "codec_vs_random_multiseed_audit.json" HEAD -- "$REGISTRY_PATH" \
  && git diff --quiet -- "$CLEAN_CONTROL_PREREG" \
  && git diff --cached --quiet -- "$CLEAN_CONTROL_PREREG" \
  && git diff --quiet -- "$REGISTRY_PATH" \
  && git diff --cached --quiet -- "$REGISTRY_PATH"; then
  clean_control_prereg_committed=1
fi

closure_record_committed=0
closure_record_path_ok=0
closure_record_dirty=0
closure_record_dir="${CLOSURE_RECORD%/*}"
closure_record_name="${CLOSURE_RECORD##*/}"
if [[ "$closure_record_dir" == "research/experiments/2026" ]] \
  && [[ "$closure_record_name" == *qwen*kr070*random*control*closure*.md ]]; then
  closure_record_path_ok=1
fi

if [[ -n "$CLOSURE_RECORD" && "$closure_record_path_ok" == "1" ]]; then
  if ! git diff --quiet -- "$CLOSURE_RECORD" \
    || ! git diff --cached --quiet -- "$CLOSURE_RECORD"; then
    closure_record_dirty=1
  fi
fi

if [[ -n "$CLOSURE_RECORD" ]] \
  && [[ "$closure_record_path_ok" == "1" ]] \
  && [[ "$(git cat-file -t "HEAD:$CLOSURE_RECORD" 2>/dev/null || true)" == "blob" ]] \
  && git grep -q --fixed-strings "OV6_ALLOW_CLOSE_RANDOM_CONTROL_WINDOW=1" HEAD -- "$CLOSURE_RECORD" \
  && git grep -q --fixed-strings "seed-42" HEAD -- "$CLOSURE_RECORD" \
  && git grep -q --fixed-strings "clean-control window" HEAD -- "$CLOSURE_RECORD" \
  && git grep -q --fixed-strings "$CLOSURE_RECORD" HEAD -- "$REGISTRY_PATH" \
  && git diff --quiet -- "$CLOSURE_RECORD" \
  && git diff --cached --quiet -- "$CLOSURE_RECORD" \
  && git diff --quiet -- "$REGISTRY_PATH" \
  && git diff --cached --quiet -- "$REGISTRY_PATH"; then
  closure_record_committed=1
fi

seed42_artifact_exists=0
for seed42_path in \
  "$OUT_DIR/uniform_random" \
  "$OUT_DIR/uniform_random/summary.json" \
  "$OUT_DIR/uniform_random/results.jsonl" \
  "$OUT_DIR/uniform_random/run.log"; do
  if [[ -e "$seed42_path" ]]; then
    seed42_artifact_exists=1
  fi
done

if [[ "$ALLOW_CLOSE_RANDOM_CONTROL_WINDOW" == "1" && "$closure_record_dirty" == "1" ]]; then
  cat >&2 <<EOF
[m5-qwen-parity] refusing to launch: closure record has staged or unstaged edits:
[m5-qwen-parity]   $CLOSURE_RECORD
[m5-qwen-parity] Commit the closure record before launch so the seed-42 random
[m5-qwen-parity] arm cannot retroactively define the closure.
EOF
  exit 2
fi

if [[ "$ALLOW_CLOSE_RANDOM_CONTROL_WINDOW" == "1" && -n "$CLOSURE_RECORD" && "$registry_dirty" == "1" ]]; then
  cat >&2 <<EOF
[m5-qwen-parity] refusing to launch: experiment registry has staged or
[m5-qwen-parity] unstaged edits:
[m5-qwen-parity]   $REGISTRY_PATH
[m5-qwen-parity] Commit the registry entry before launch so the seed-42 random
[m5-qwen-parity] arm cannot retroactively define the closure.
EOF
  exit 2
fi

if [[ "$ALLOW_CLOSE_RANDOM_CONTROL_WINDOW" == "1" && "$closure_record_committed" != "1" ]]; then
  cat >&2 <<EOF
[m5-qwen-parity] refusing to launch: OV6_ALLOW_CLOSE_RANDOM_CONTROL_WINDOW=1
[m5-qwen-parity] requires a committed closure record, clean in the worktree/index,
[m5-qwen-parity] named in the experiment registry, and matching:
[m5-qwen-parity]   research/experiments/2026/*qwen*kr070*random*control*closure*.md
[m5-qwen-parity] The closure record must name OV6_ALLOW_CLOSE_RANDOM_CONTROL_WINDOW=1,
[m5-qwen-parity] seed-42, and the clean-control window.
[m5-qwen-parity] For example:
[m5-qwen-parity]   OV6_ALLOW_CLOSE_RANDOM_CONTROL_WINDOW=1 OV6_CLOSURE_RECORD=research/experiments/2026/2026-05-26-qwen-kr070-random-control-closure.md scripts/run_ov6_m5_qwen_parity.sh
EOF
  exit 2
fi

if [[ "$ALLOW_CLOSE_RANDOM_CONTROL_WINDOW" != "1" && "$clean_control_prereg_dirty" == "1" ]]; then
  cat >&2 <<EOF
[m5-qwen-parity] refusing to launch: clean-control preregistration has staged
[m5-qwen-parity] or unstaged edits:
[m5-qwen-parity]   $CLEAN_CONTROL_PREREG
[m5-qwen-parity] Commit the preregistration before launch so the seed-42
[m5-qwen-parity] random arm cannot retroactively define the control.
EOF
  exit 2
fi

if [[ "$ALLOW_CLOSE_RANDOM_CONTROL_WINDOW" != "1" && "$clean_control_prereg_path_ok" == "1" && "$registry_dirty" == "1" ]]; then
  cat >&2 <<EOF
[m5-qwen-parity] refusing to launch: experiment registry has staged or
[m5-qwen-parity] unstaged edits:
[m5-qwen-parity]   $REGISTRY_PATH
[m5-qwen-parity] Commit the registry entry before launch so the seed-42
[m5-qwen-parity] random arm cannot retroactively define the control.
EOF
  exit 2
fi

if [[ "$ALLOW_CLOSE_RANDOM_CONTROL_WINDOW" != "1" && "$clean_control_prereg_committed" == "1" && "$out_dir_overridden" == "1" ]]; then
  cat >&2 <<EOF
[m5-qwen-parity] refusing to launch: M5Q_OUT_DIR override is not allowed on the
[m5-qwen-parity] clean-control path.
[m5-qwen-parity] Canonical parity root:
[m5-qwen-parity]   $CANONICAL_OUT_DIR
[m5-qwen-parity] Requested root:
[m5-qwen-parity]   $OUT_DIR
[m5-qwen-parity] Use the canonical root before seed-42 closes the clean-control
[m5-qwen-parity] window, or explicitly accept closure with
[m5-qwen-parity] OV6_ALLOW_CLOSE_RANDOM_CONTROL_WINDOW=1 plus a committed
[m5-qwen-parity] closure record.
EOF
  exit 2
fi

if [[ "$ALLOW_CLOSE_RANDOM_CONTROL_WINDOW" != "1" && "$clean_control_prereg_committed" == "1" && "$seed42_artifact_exists" == "1" ]]; then
  cat >&2 <<EOF
[m5-qwen-parity] refusing to launch: seed-42 parity artifacts already exist under
[m5-qwen-parity] $OUT_DIR. Checked:
[m5-qwen-parity]   $OUT_DIR/uniform_random
[m5-qwen-parity]   $OUT_DIR/uniform_random/summary.json
[m5-qwen-parity]   $OUT_DIR/uniform_random/results.jsonl
[m5-qwen-parity]   $OUT_DIR/uniform_random/run.log
[m5-qwen-parity] The clean four-seed random-control window is closed. Use the
[m5-qwen-parity] committed closure-record path instead:
[m5-qwen-parity]   OV6_ALLOW_CLOSE_RANDOM_CONTROL_WINDOW=1 OV6_CLOSURE_RECORD=<committed repo-relative closure path> scripts/run_ov6_m5_qwen_parity.sh
EOF
  exit 2
fi

if [[ "$ALLOW_CLOSE_RANDOM_CONTROL_WINDOW" != "1" && "$clean_control_prereg_committed" != "1" ]]; then
  cat >&2 <<EOF
[m5-qwen-parity] refusing to launch: without a complete, committed clean-control
[m5-qwen-parity] preregistration and registry entry, this script's seed-42
[m5-qwen-parity] uniform_random arm closes the clean four-seed random-control window.
[m5-qwen-parity] Commit the clean-control preregistration first, leave it with no
[m5-qwen-parity] staged or unstaged edits, and point to it with a path matching:
[m5-qwen-parity]   research/experiments/2026/*qwen*kr070*random*control*prereg.md
[m5-qwen-parity] Use the repo-relative path exactly; absolute paths and ./-prefixed
[m5-qwen-parity] paths are rejected.
[m5-qwen-parity] The committed file must be a blob and must name dense/,
[m5-qwen-parity] magnitude_norm/, codec_novel_coded/, the four seed output
[m5-qwen-parity] directories, and codec_vs_random_multiseed_audit.json.
[m5-qwen-parity] The committed, clean experiment registry must also name that
[m5-qwen-parity] preregistration path plus the comparator and random arm paths.
[m5-qwen-parity] This refusal can mean the preregistration is missing or
[m5-qwen-parity] incomplete, the registry is missing or incomplete, or either
[m5-qwen-parity] file has staged or unstaged edits.
[m5-qwen-parity] Required registry arm-path strings:
[m5-qwen-parity]   m5_ov6_qwen_n57_kr070_l2_random_control/dense/
[m5-qwen-parity]   m5_ov6_qwen_n57_kr070_l2_random_control/magnitude_norm/
[m5-qwen-parity]   m5_ov6_qwen_n57_kr070_l2_random_control/codec_novel_coded/
[m5-qwen-parity]   m5_ov6_qwen_n57_kr070_l2_random_control/uniform_random_seed1/
[m5-qwen-parity]   m5_ov6_qwen_n57_kr070_l2_random_control/uniform_random_seed7/
[m5-qwen-parity]   m5_ov6_qwen_n57_kr070_l2_random_control/uniform_random_seed42/
[m5-qwen-parity]   m5_ov6_qwen_n57_kr070_l2_random_control/uniform_random_seed100/
[m5-qwen-parity] Launch after setting M5Q_CLEAN_CONTROL_PREREG to the committed,
[m5-qwen-parity] repo-relative preregistration path.
[m5-qwen-parity]   M5Q_CLEAN_CONTROL_PREREG=<committed repo-relative preregistration path> scripts/run_ov6_m5_qwen_parity.sh
[m5-qwen-parity] Or explicitly accept the closure with:
[m5-qwen-parity]   OV6_ALLOW_CLOSE_RANDOM_CONTROL_WINDOW=1 OV6_CLOSURE_RECORD=<committed repo-relative closure path> scripts/run_ov6_m5_qwen_parity.sh
EOF
  exit 2
fi

if [[ "${OV6_PREFLIGHT_ONLY:-0}" == "1" ]]; then
  echo "[m5-qwen-parity] preflight passed"
  exit 0
fi

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
