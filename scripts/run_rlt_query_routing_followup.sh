#!/usr/bin/env bash
set -euo pipefail

# Launch the narrow post-Q1 query-routing follow-up on the local Gemma setup.
# This intentionally runs only the already-preregistered Q0b/Q1 gates plus Q1b:
# endpoint anchors, admission-on coverage controls, and one dense-fallback
# coverage repair. It does not run QuoTA, repair-pass, or full planner work.

cd "$(dirname "$0")/.."

PY="${PYTHON:-./.venv/bin/python}"
MODEL_PATH="${GEMMA_MODEL_PATH:-$HOME/models/gemma-4-e4b-it-4bit}"
ARTIFACT_DIR="${ARTIFACT_DIR:-research/experiments/2026/artifacts/rlt_query_routing_first_branch}"
QUERY_ROUTING_BENCHMARKS="${QUERY_ROUTING_BENCHMARKS:-mvbench}"
MLX_MEMORY_LIMIT_GB="${MLX_MEMORY_LIMIT_GB:-12}"
RSS_GUARD_MB="${RSS_GUARD_MB:-9000}"

for arg in "$@"; do
  case "$arg" in
    --dry-run|--summary|--summary=*|--max-planned-hours|--max-planned-hours=*)
      ;;
    --*)
      echo "Refusing out-of-scope queue override in query-routing follow-up wrapper: $arg" >&2
      echo "Use GEMMA_MODEL_PATH, ARTIFACT_DIR, QUERY_ROUTING_BENCHMARKS, MLX_MEMORY_LIMIT_GB, or RSS_GUARD_MB env vars for scoped overrides." >&2
      exit 2
      ;;
  esac
done

exec "$PY" scripts/run_rlt_followup_queue.py \
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
