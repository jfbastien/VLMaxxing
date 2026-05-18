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
MARGIN_FIELD="${MARGIN_FIELD:-composed_first_generated_candidate_top2_margin}"
QUALITY_DELTA_FLOOR="${QUALITY_DELTA_FLOOR:--0.05}"
MIN_SPEEDUP="${MIN_SPEEDUP:-1.0}"

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
      echo "Use GEMMA_MODEL_PATH, ARTIFACT_DIR, QUERY_ROUTING_BENCHMARKS, MLX_MEMORY_LIMIT_GB, RSS_GUARD_MB, MARGIN_FIELD, QUALITY_DELTA_FLOOR, or MIN_SPEEDUP env vars for scoped overrides." >&2
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

if [[ "$DRY_RUN" == "1" ]]; then
  exit 0
fi

"$PY" scripts/analyze_gemma_active_repair_confidence.py \
  --paired-items "$ARTIFACT_DIR/query_q1b_mvbench_random_seed11_admission_on_paired.jsonl" \
  --output "$ARTIFACT_DIR/query_q1b_mvbench_random_seed11_admission_on_active_repair_confidence.json" \
  --margin-field "$MARGIN_FIELD" \
  --quality-delta-floor "$QUALITY_DELTA_FLOOR" \
  --min-speedup "$MIN_SPEEDUP"

"$PY" scripts/analyze_gemma_active_repair_confidence.py \
  --paired-items "$ARTIFACT_DIR/query_q1b_mvbench_fixed_uniform_admission_on_paired.jsonl" \
  --output "$ARTIFACT_DIR/query_q1b_mvbench_fixed_uniform_admission_on_active_repair_confidence.json" \
  --margin-field "$MARGIN_FIELD" \
  --quality-delta-floor "$QUALITY_DELTA_FLOOR" \
  --min-speedup "$MIN_SPEEDUP"
