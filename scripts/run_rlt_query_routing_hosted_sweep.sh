#!/usr/bin/env bash
set -euo pipefail

# Launch the broader MVBench-hosted Q1 sweep. This expands the static-operator
# negative-control check from the five motion buckets to the existing 54-item,
# 18-bucket hosted slice. It intentionally does not run Q1b/Q1c, codec routing,
# repair, QuoTA-style scalar routing, or holdout confirmation.

cd "$(dirname "$0")/.."

PY="${PYTHON:-./.venv/bin/python}"
MODEL_PATH="${GEMMA_MODEL_PATH:-$HOME/models/gemma-4-e4b-it-4bit}"
ARTIFACT_DIR="${ARTIFACT_DIR:-research/experiments/2026/artifacts/rlt_query_routing_hosted_sweep}"
MVBENCH_MANIFEST="${MVBENCH_MANIFEST:-research/benchmark_manifests/mvbench_hosted_dev_v1.toml}"
MLX_MEMORY_LIMIT_GB="${MLX_MEMORY_LIMIT_GB:-12}"
RSS_GUARD_MB="${RSS_GUARD_MB:-9000}"

for arg in "$@"; do
  case "$arg" in
    --dry-run|--summary|--summary=*|--max-planned-hours|--max-planned-hours=*)
      ;;
    --*)
      echo "Refusing out-of-scope queue override in hosted query-routing wrapper: $arg" >&2
      echo "Use GEMMA_MODEL_PATH, ARTIFACT_DIR, MVBENCH_MANIFEST, MLX_MEMORY_LIMIT_GB, or RSS_GUARD_MB env vars for scoped overrides." >&2
      exit 2
      ;;
  esac
done

exec "$PY" scripts/run_rlt_followup_queue.py \
  --gemma-model-path "$MODEL_PATH" \
  --artifact-dir "$ARTIFACT_DIR" \
  --mvbench-manifest "$MVBENCH_MANIFEST" \
  --mlx-memory-limit-gb "$MLX_MEMORY_LIMIT_GB" \
  --rss-guard-mb "$RSS_GUARD_MB" \
  --run-cvision-rlt \
  --run-query-routing-q0b \
  --run-query-routing-q1 \
  --query-routing-benchmarks mvbench \
  "$@"
