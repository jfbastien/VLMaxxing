#!/usr/bin/env bash
set -euo pipefail

# Launch the bounded M3 Gemma cost-accounting follow-up queue. The default
# core tier runs only VideoMME-short admission keep-rate bracketing. Set
# M3_FOLLOWUP_TIER=extended to add MVBench-hosted bracketing plus TOMATO and
# VideoMME-short RLT-composition checks. This wrapper intentionally exposes no
# query-routing, active-repair, M5, rescue, or broad composition toggles.

cd "$(dirname "$0")/.."

PY="${PYTHON:-./.venv/bin/python}"
MODEL_PATH="${GEMMA_MODEL_PATH:-$HOME/models/gemma-4-e4b-it-4bit}"
ARTIFACT_DIR="${ARTIFACT_DIR:-research/experiments/2026/artifacts/rlt_m3_cost_accounting_followup}"
MLX_MEMORY_LIMIT_GB="${MLX_MEMORY_LIMIT_GB:-12}"
RSS_GUARD_MB="${RSS_GUARD_MB:-9000}"
N_ITEMS="${N_ITEMS:-0}"
M3_FOLLOWUP_TIER="${M3_FOLLOWUP_TIER:-core}"

case "$M3_FOLLOWUP_TIER" in
  core|extended)
    ;;
  *)
    echo "Refusing unknown M3_FOLLOWUP_TIER: $M3_FOLLOWUP_TIER" >&2
    exit 2
    ;;
esac

case "$N_ITEMS" in
  ''|*[!0-9]*)
    echo "Refusing non-integer N_ITEMS: $N_ITEMS" >&2
    exit 2
    ;;
esac

for arg in "$@"; do
  case "$arg" in
    --dry-run|--summary|--summary=*|--max-planned-hours|--max-planned-hours=*)
      ;;
    --*)
      echo "Refusing out-of-scope queue override in M3 cost-accounting wrapper: $arg" >&2
      echo "Use GEMMA_MODEL_PATH, ARTIFACT_DIR, MLX_MEMORY_LIMIT_GB, RSS_GUARD_MB, N_ITEMS, or M3_FOLLOWUP_TIER env vars for scoped overrides." >&2
      exit 2
      ;;
  esac
done

exec "$PY" scripts/run_rlt_m3_cost_accounting_followup.py \
  --gemma-model-path "$MODEL_PATH" \
  --artifact-dir "$ARTIFACT_DIR" \
  --mlx-memory-limit-gb "$MLX_MEMORY_LIMIT_GB" \
  --rss-guard-mb "$RSS_GUARD_MB" \
  --n-items "$N_ITEMS" \
  --tier "$M3_FOLLOWUP_TIER" \
  "$@"
