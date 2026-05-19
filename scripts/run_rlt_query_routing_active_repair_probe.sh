#!/usr/bin/env bash
set -euo pipefail

# Run the narrow Q1b admission-on follow-up with first-token confidence capture,
# then simulate one-step active repair from the paired artifacts. This is the
# publish-or-kill probe for "does the cheap pass know when to retry?"

cd "$(dirname "$0")/.."

PY="${PYTHON:-./.venv/bin/python}"
MODEL_PATH="${GEMMA_MODEL_PATH:-$HOME/models/gemma-4-e4b-it-4bit}"
ARTIFACT_DIR="${ARTIFACT_DIR:-research/experiments/2026/artifacts/rlt_query_routing_active_repair_probe}"
QUERY_ROUTING_BENCHMARKS="${QUERY_ROUTING_BENCHMARKS:-mvbench}"
MLX_MEMORY_LIMIT_GB="${MLX_MEMORY_LIMIT_GB:-12}"
RSS_GUARD_MB="${RSS_GUARD_MB:-9000}"
MARGIN_FIELD="${MARGIN_FIELD:-composed_first_generated_top2_margin}"
QUALITY_DELTA_FLOOR="${QUALITY_DELTA_FLOOR:--0.02}"
MIN_SPEEDUP="${MIN_SPEEDUP:-1.254}"
MAX_RETRY_RATE="${MAX_RETRY_RATE:-0.50}"
MIN_HARMED_RETRIED="${MIN_HARMED_RETRIED:-2}"
MIN_AUC_LOWER_CI="${MIN_AUC_LOWER_CI:-0.65}"
MIN_AUC_CLASS_COUNT="${MIN_AUC_CLASS_COUNT:-3}"
ACTIVE_REPAIR_N_BOOTSTRAP="${ACTIVE_REPAIR_N_BOOTSTRAP:-2000}"
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
    --summary|--summary=*|--max-planned-hours|--max-planned-hours=*)
      ;;
    --*)
      echo "Refusing out-of-scope queue override in active-repair probe wrapper: $arg" >&2
      echo "Use GEMMA_MODEL_PATH, ARTIFACT_DIR, QUERY_ROUTING_BENCHMARKS, MLX_MEMORY_LIMIT_GB, RSS_GUARD_MB, MARGIN_FIELD, QUALITY_DELTA_FLOOR, MIN_SPEEDUP, MAX_RETRY_RATE, MIN_HARMED_RETRIED, MIN_AUC_LOWER_CI, MIN_AUC_CLASS_COUNT, ACTIVE_REPAIR_N_BOOTSTRAP, or BASELINE_REPAIR_PAIRED env vars for scoped overrides." >&2
      exit 2
      ;;
  esac
done

"$PY" scripts/run_rlt_followup_queue.py \
  --gemma-model-path "$MODEL_PATH" \
  --artifact-dir "$ARTIFACT_DIR" \
  --mlx-memory-limit-gb "$MLX_MEMORY_LIMIT_GB" \
  --rss-guard-mb "$RSS_GUARD_MB" \
  --run-cvision-rlt \
  --run-query-routing-q0b \
  --run-query-routing-q1 \
  --run-query-routing-q1b-followup \
  --query-routing-benchmarks "$QUERY_ROUTING_BENCHMARKS" \
  "$@"

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
if [[ -n "$BASELINE_REPAIR_PAIRED" ]]; then
  repair_common_args+=(--baseline-paired-items "$BASELINE_REPAIR_PAIRED")
fi

run_repair_analyzer() {
  local paired_items="$1"
  local output="$2"
  if [[ "$DRY_RUN" == "1" ]]; then
    printf '[dry-run]'
    printf ' %q' "$PY" scripts/analyze_gemma_active_repair_confidence.py \
      --paired-items "$paired_items" \
      --output "$output" \
      "${repair_common_args[@]}"
    printf '\n'
    return 0
  fi
  if [[ ! -s "$paired_items" ]]; then
    echo "Expected paired artifact missing after queue run: $paired_items" >&2
    exit 2
  fi
  "$PY" scripts/analyze_gemma_active_repair_confidence.py \
    --paired-items "$paired_items" \
    --output "$output" \
    "${repair_common_args[@]}"
}

run_repair_analyzer \
  "$ARTIFACT_DIR/query_q1b_mvbench_random_seed11_admission_on_paired.jsonl" \
  "$ARTIFACT_DIR/query_q1b_mvbench_random_seed11_admission_on_active_repair_confidence.json"

run_repair_analyzer \
  "$ARTIFACT_DIR/query_q1b_mvbench_fixed_uniform_admission_on_paired.jsonl" \
  "$ARTIFACT_DIR/query_q1b_mvbench_fixed_uniform_admission_on_active_repair_confidence.json"

if [[ "$DRY_RUN" == "1" ]]; then
  printf '[dry-run]'
  printf ' %q' "$PY" scripts/analyze_gemma_active_repair_confidence.py \
    --paired-items "$ARTIFACT_DIR/query_q1b_mvbench_random_seed11_admission_on_paired.jsonl" \
    --paired-items "$ARTIFACT_DIR/query_q1b_mvbench_fixed_uniform_admission_on_paired.jsonl" \
    --output "$ARTIFACT_DIR/query_q1b_mvbench_admission_on_pooled_active_repair_confidence.json" \
    "${repair_common_args[@]}"
  printf '\n'
else
  for paired_items in \
    "$ARTIFACT_DIR/query_q1b_mvbench_random_seed11_admission_on_paired.jsonl" \
    "$ARTIFACT_DIR/query_q1b_mvbench_fixed_uniform_admission_on_paired.jsonl"; do
    if [[ ! -s "$paired_items" ]]; then
      echo "Expected paired artifact missing after queue run: $paired_items" >&2
      exit 2
    fi
  done
  "$PY" scripts/analyze_gemma_active_repair_confidence.py \
    --paired-items "$ARTIFACT_DIR/query_q1b_mvbench_random_seed11_admission_on_paired.jsonl" \
    --paired-items "$ARTIFACT_DIR/query_q1b_mvbench_fixed_uniform_admission_on_paired.jsonl" \
    --output "$ARTIFACT_DIR/query_q1b_mvbench_admission_on_pooled_active_repair_confidence.json" \
    "${repair_common_args[@]}"
fi
