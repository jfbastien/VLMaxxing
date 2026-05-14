#!/usr/bin/env bash
set -euo pipefail

# Launch the Gemma-family M5 scale-confirmation queue. This is not a discovery
# queue: it tests scorer transfer and C-CEILING scale behavior using the same
# paper setup Sam has been running. The operator must provide the exact model
# path on that machine.

cd "$(dirname "$0")/.."

: "${GEMMA_MODEL_PATH:?Set GEMMA_MODEL_PATH to the verified local Gemma 4 26B-A4B MLX model path}"

PY="${PYTHON:-./.venv/bin/python}"
ARTIFACT_DIR="${ARTIFACT_DIR:-research/experiments/2026/artifacts/rlt_followup_queue_m5_gemma4_26b}"
MLX_MEMORY_LIMIT_GB="${MLX_MEMORY_LIMIT_GB:-60}"
RSS_GUARD_MB="${RSS_GUARD_MB:-60000}"
FRAME_COUNT="${FRAME_COUNT:-8}"

for arg in "$@"; do
  case "$arg" in
    --dry-run|--summary|--summary=*|--max-planned-hours|--max-planned-hours=*)
      ;;
    --*)
      echo "Refusing out-of-scope queue override in M5 scale-confirmation wrapper: $arg" >&2
      echo "Use GEMMA_MODEL_PATH, ARTIFACT_DIR, MLX_MEMORY_LIMIT_GB, RSS_GUARD_MB, or FRAME_COUNT env vars for scoped overrides." >&2
      exit 2
      ;;
  esac
done

exec "$PY" scripts/run_rlt_followup_queue.py \
  --gemma-model-path "$GEMMA_MODEL_PATH" \
  --artifact-dir "$ARTIFACT_DIR" \
  --mlx-memory-limit-gb "$MLX_MEMORY_LIMIT_GB" \
  --rss-guard-mb "$RSS_GUARD_MB" \
  --frame-count "$FRAME_COUNT" \
  --run-cvision-rlt \
  --run-cvision-expansion \
  --run-max-min-triangulation \
  --run-magnitude-valid-head-to-head \
  "$@"
