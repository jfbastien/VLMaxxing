#!/usr/bin/env bash
set -euo pipefail

# Launch the narrow Q1c admission-scheduler follow-up on the local Gemma setup.
# This intentionally resumes the already-preregistered Q0b/Q1/Q1b gates and
# then runs only Q1c: coverage-first random C-VISION, prompt admission off by
# default, and admission enabled only for preregistered low-risk groups. It does
# not run QuoTA, repair-pass, learned planners, or extra benchmarks.

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
      echo "Refusing out-of-scope queue override in query-routing admission-scheduler wrapper: $arg" >&2
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
  --run-query-routing-q1c-admission-scheduler \
  --query-routing-benchmarks "$QUERY_ROUTING_BENCHMARKS" \
  "$@"
