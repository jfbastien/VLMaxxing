#!/usr/bin/env bash
set -euo pipefail

# Run only the active-repair confidence probe cells:
#   1. shared dense/no-admission baseline;
#   2. random_valid(seed=11) + admission-off same-run baseline;
#   3. random_valid(seed=11) + admission-on cheap pass;
#   4. fixed_uniform + admission-on cheap pass;
#   5. paired analyzers for all three non-dense arms;
#   6. confidence-frontier analyzers for both admission-on arms and their pool.
#
# This intentionally avoids the broad Q0b/Q1/Q1b dependency chain. Use it when
# those prerequisites are already understood and the next question is narrowly:
# does first-pass confidence identify rows that should retry with dense, while
# beating a same-run random_valid(seed=11) admission-off baseline?

cd "$(dirname "$0")/.."

PY="${PYTHON:-./.venv/bin/python}"
MODEL_PATH="${GEMMA_MODEL_PATH:-$HOME/models/gemma-4-e4b-it-4bit}"
MVBENCH_MANIFEST="${MVBENCH_MANIFEST:-research/benchmark_manifests/mvbench_motion_dev_v2.toml}"
FRAME_COUNT="${FRAME_COUNT:-8}"
PREFILL_STEP_SIZE="${PREFILL_STEP_SIZE:-1024}"
MLX_MEMORY_LIMIT_GB="${MLX_MEMORY_LIMIT_GB:-12}"
RSS_GUARD_MB="${RSS_GUARD_MB:-9000}"
N_ITEMS="${N_ITEMS:-0}"
MARGIN_FIELD="${MARGIN_FIELD:-composed_first_generated_candidate_top2_margin}"
QUALITY_DELTA_FLOOR="${QUALITY_DELTA_FLOOR:--0.02}"
MIN_SPEEDUP="${MIN_SPEEDUP:-1.0}"
MAX_RETRY_RATE="${MAX_RETRY_RATE:-0.50}"
MIN_HARMED_RETRIED="${MIN_HARMED_RETRIED:-2}"
MIN_AUC_LOWER_CI="${MIN_AUC_LOWER_CI:-0.65}"
MIN_AUC_CLASS_COUNT="${MIN_AUC_CLASS_COUNT:-3}"
BASELINE_REPAIR_PAIRED="${BASELINE_REPAIR_PAIRED:-}"

case "$MARGIN_FIELD" in
  composed_first_generated_candidate_top2_margin|composed_first_generated_top2_margin|composed_first_generated_selected_margin)
    ;;
  *)
    echo "Refusing margin field outside composed first-generated confidence fields: $MARGIN_FIELD" >&2
    exit 2
    ;;
esac

DRY_RUN=0
for arg in "$@"; do
  case "$arg" in
    --dry-run)
      DRY_RUN=1
      ;;
    --*)
      echo "Refusing out-of-scope queue override in active-repair targeted wrapper: $arg" >&2
      echo "Use GEMMA_MODEL_PATH, ARTIFACT_DIR, MVBENCH_MANIFEST, FRAME_COUNT, PREFILL_STEP_SIZE, MLX_MEMORY_LIMIT_GB, RSS_GUARD_MB, EXPECTED_ITEMS, BUCKET_MIN_N, N_BOOTSTRAP, ACTIVE_REPAIR_N_BOOTSTRAP, MARGIN_FIELD, QUALITY_DELTA_FLOOR, MIN_SPEEDUP, MAX_RETRY_RATE, MIN_HARMED_RETRIED, MIN_AUC_LOWER_CI, MIN_AUC_CLASS_COUNT, or BASELINE_REPAIR_PAIRED env vars for scoped overrides." >&2
      exit 2
      ;;
  esac
done

case "$N_ITEMS" in
  ''|*[!0-9]*)
    echo "Refusing non-integer N_ITEMS: $N_ITEMS" >&2
    exit 2
    ;;
esac

if [[ -z "${EXPECTED_ITEMS+x}" ]]; then
  if [[ "$N_ITEMS" == "0" ]]; then
    EXPECTED_ITEMS=30
  else
    EXPECTED_ITEMS="$N_ITEMS"
  fi
fi
if [[ -z "${BUCKET_MIN_N+x}" ]]; then
  if [[ "$N_ITEMS" == "0" ]]; then
    BUCKET_MIN_N=5
  else
    BUCKET_MIN_N=1
  fi
fi
if [[ -z "${N_BOOTSTRAP+x}" ]]; then
  if [[ "$N_ITEMS" == "0" ]]; then
    N_BOOTSTRAP=500
  else
    N_BOOTSTRAP=50
  fi
fi
if [[ -z "${ACTIVE_REPAIR_N_BOOTSTRAP+x}" ]]; then
  if [[ "$N_ITEMS" == "0" ]]; then
    ACTIVE_REPAIR_N_BOOTSTRAP=2000
  else
    ACTIVE_REPAIR_N_BOOTSTRAP=100
  fi
fi
if [[ -z "${ARTIFACT_DIR+x}" ]]; then
  if [[ "$N_ITEMS" == "0" ]]; then
    ARTIFACT_DIR="research/experiments/2026/artifacts/rlt_query_routing_active_repair_targeted"
  else
    ARTIFACT_DIR="research/experiments/2026/artifacts/rlt_query_routing_active_repair_targeted_smoke"
  fi
fi

if [[ "$DRY_RUN" != "1" ]]; then
  mkdir -p "$ARTIFACT_DIR"
fi

DENSE_JSONL="$ARTIFACT_DIR/query_q1b_dense_mvbench_dense.jsonl"
DENSE_SUMMARY="$ARTIFACT_DIR/query_q1b_dense_mvbench_dense_summary.json"
RANDOM_JSONL="$ARTIFACT_DIR/query_q1b_mvbench_random_seed11_admission_on_composed.jsonl"
RANDOM_SUMMARY="$ARTIFACT_DIR/query_q1b_mvbench_random_seed11_admission_on_composed_summary.json"
RANDOM_ANALYSIS="$ARTIFACT_DIR/query_q1b_mvbench_random_seed11_admission_on_analysis.json"
RANDOM_PAIRED="$ARTIFACT_DIR/query_q1b_mvbench_random_seed11_admission_on_paired.jsonl"
RANDOM_REPAIR="$ARTIFACT_DIR/query_q1b_mvbench_random_seed11_admission_on_active_repair_confidence.json"
BASELINE_JSONL="$ARTIFACT_DIR/query_q1_mvbench_random_seed11_no_admission_composed.jsonl"
BASELINE_SUMMARY="$ARTIFACT_DIR/query_q1_mvbench_random_seed11_no_admission_composed_summary.json"
BASELINE_ANALYSIS="$ARTIFACT_DIR/query_q1_mvbench_random_seed11_no_admission_analysis.json"
BASELINE_PAIRED="$ARTIFACT_DIR/query_q1_mvbench_random_seed11_no_admission_paired.jsonl"
FIXED_JSONL="$ARTIFACT_DIR/query_q1b_mvbench_fixed_uniform_admission_on_composed.jsonl"
FIXED_SUMMARY="$ARTIFACT_DIR/query_q1b_mvbench_fixed_uniform_admission_on_composed_summary.json"
FIXED_ANALYSIS="$ARTIFACT_DIR/query_q1b_mvbench_fixed_uniform_admission_on_analysis.json"
FIXED_PAIRED="$ARTIFACT_DIR/query_q1b_mvbench_fixed_uniform_admission_on_paired.jsonl"
FIXED_REPAIR="$ARTIFACT_DIR/query_q1b_mvbench_fixed_uniform_admission_on_active_repair_confidence.json"
POOLED_REPAIR="$ARTIFACT_DIR/query_q1b_mvbench_admission_on_pooled_active_repair_confidence.json"

run_or_print() {
  if [[ "$DRY_RUN" == "1" ]]; then
    printf '[dry-run]'
    printf ' %q' "$@"
    printf '\n'
  else
    "$@"
  fi
}

base_args=(
  "$PY" scripts/run_novelty_pruning_gemma.py
  --manifest "$MVBENCH_MANIFEST"
  --frame-count "$FRAME_COUNT"
  --anchor-arm gemma_structural
  --prefill-step-size "$PREFILL_STEP_SIZE"
  --model-path "$MODEL_PATH"
  --rss-guard-mb "$RSS_GUARD_MB"
  --mlx-memory-limit-gb "$MLX_MEMORY_LIMIT_GB"
  --n-warmup 1
  --arm-order abba
  --resume
)

if [[ "$N_ITEMS" != "0" ]]; then
  base_args+=(--n-items "$N_ITEMS")
fi

repair_common_args=(
  --margin-field "$MARGIN_FIELD"
  --quality-delta-floor "$QUALITY_DELTA_FLOOR"
  --min-speedup "$MIN_SPEEDUP"
  --max-retry-rate "$MAX_RETRY_RATE"
  --min-harmed-retried "$MIN_HARMED_RETRIED"
  --min-auc-lower-ci "$MIN_AUC_LOWER_CI"
  --min-auc-class-count "$MIN_AUC_CLASS_COUNT"
  --n-bootstrap "$ACTIVE_REPAIR_N_BOOTSTRAP"
)
if [[ -z "$BASELINE_REPAIR_PAIRED" ]]; then
  BASELINE_REPAIR_PAIRED="$BASELINE_PAIRED"
fi
repair_common_args+=(--baseline-paired-items "$BASELINE_REPAIR_PAIRED")

run_or_print "${base_args[@]}" \
  --keep-rate 1.0 \
  --prune-placeholders none \
  --vision-tower-keep-rate 1.0 \
  --output "$DENSE_JSONL" \
  --summary "$DENSE_SUMMARY"

run_or_print "${base_args[@]}" \
  --keep-rate 1.0 \
  --prune-placeholders none \
  --vision-tower-keep-rate 0.5 \
  --vision-tower-score-mode random_valid \
  --vision-random-seed 11 \
  --output "$BASELINE_JSONL" \
  --summary "$BASELINE_SUMMARY"

run_or_print "$PY" scripts/analyze_gemma_full_composition.py \
  --dense-jsonl "$DENSE_JSONL" \
  --composed-jsonl "$BASELINE_JSONL" \
  --dense-source composed-jsonl-same-run \
  --output "$BASELINE_ANALYSIS" \
  --paired-items "$BASELINE_PAIRED" \
  --expected-items "$EXPECTED_ITEMS" \
  --bucket-min-n "$BUCKET_MIN_N" \
  --n-bootstrap "$N_BOOTSTRAP"

run_or_print "${base_args[@]}" \
  --keep-rate 0.5 \
  --prune-placeholders rlt \
  --vision-tower-keep-rate 0.5 \
  --vision-tower-score-mode random_valid \
  --vision-random-seed 11 \
  --output "$RANDOM_JSONL" \
  --summary "$RANDOM_SUMMARY"

run_or_print "$PY" scripts/analyze_gemma_full_composition.py \
  --dense-jsonl "$DENSE_JSONL" \
  --composed-jsonl "$RANDOM_JSONL" \
  --dense-source composed-jsonl-same-run \
  --output "$RANDOM_ANALYSIS" \
  --paired-items "$RANDOM_PAIRED" \
  --expected-items "$EXPECTED_ITEMS" \
  --bucket-min-n "$BUCKET_MIN_N" \
  --n-bootstrap "$N_BOOTSTRAP"

run_or_print "${base_args[@]}" \
  --keep-rate 0.5 \
  --prune-placeholders rlt \
  --vision-tower-keep-rate 0.5 \
  --vision-tower-score-mode fixed_uniform \
  --output "$FIXED_JSONL" \
  --summary "$FIXED_SUMMARY"

run_or_print "$PY" scripts/analyze_gemma_full_composition.py \
  --dense-jsonl "$DENSE_JSONL" \
  --composed-jsonl "$FIXED_JSONL" \
  --dense-source composed-jsonl-same-run \
  --output "$FIXED_ANALYSIS" \
  --paired-items "$FIXED_PAIRED" \
  --expected-items "$EXPECTED_ITEMS" \
  --bucket-min-n "$BUCKET_MIN_N" \
  --n-bootstrap "$N_BOOTSTRAP"

run_or_print "$PY" scripts/analyze_gemma_active_repair_confidence.py \
  --paired-items "$RANDOM_PAIRED" \
  --output "$RANDOM_REPAIR" \
  "${repair_common_args[@]}"

run_or_print "$PY" scripts/analyze_gemma_active_repair_confidence.py \
  --paired-items "$FIXED_PAIRED" \
  --output "$FIXED_REPAIR" \
  "${repair_common_args[@]}"

run_or_print "$PY" scripts/analyze_gemma_active_repair_confidence.py \
  --paired-items "$RANDOM_PAIRED" \
  --paired-items "$FIXED_PAIRED" \
  --output "$POOLED_REPAIR" \
  "${repair_common_args[@]}"
