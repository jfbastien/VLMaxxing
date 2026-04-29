#!/usr/bin/env bash
# Phase 1.30 root-cause 2x2 decomposition runner.
#
# Runs six arms on the same manifest(s) so we can factorize the 1.30 negative
# result into V-only cost (pruning), K-only cost (persistent-KV reuse), their
# interaction, and whether hard-reset recovers the reuse-drift component.
#
#   cold_dense                = no reuse, no pruning (baseline)
#   cold_pruned               = no reuse, kr_V=0.50 (V-only)
#   streaming_dense_off       = KV reuse, no pruning (K-only, no refresh)
#   streaming_pruned_off      = KV reuse, kr_V=0.50 (combined, no refresh = current 1.30)
#   streaming_dense_reset     = KV reuse, no pruning, hard-reset each Q (upper-bound K recovery)
#   streaming_pruned_reset    = KV reuse, kr_V=0.50, hard-reset (combined upper-bound)
#
# MODE selects the manifest scope:
#   MODE=short (default) — videomme_dev_v1_short_only.toml (fast scout)
#   MODE=full            — dev+holdout union (confirmation run; only after scout is readable)
#
# Usage:
#   bash scripts/run_phase1_30_rootcause_decompose.sh                 # short scout
#   MODE=full bash scripts/run_phase1_30_rootcause_decompose.sh       # full confirmation

set -euo pipefail

cd "$(dirname "$0")/.."

PY="${PYTHON:-./.venv/bin/python}"
MODEL_PATH="${MODEL_PATH:-$HOME/models/Qwen2.5-VL-7B-Instruct-4bit}"
RSS_GUARD_MB="${RSS_GUARD_MB:-10000}"
MODE="${MODE:-short}"

if [[ "$MODE" == "short" ]]; then
  OUT="${OUT:-research/experiments/2026/artifacts/phase1_30_rootcause_short}"
  MANIFEST_ARGS=(
    --manifest research/benchmark_manifests/videomme_dev_v1_short_only.toml
  )
elif [[ "$MODE" == "full" ]]; then
  OUT="${OUT:-research/experiments/2026/artifacts/phase1_30_rootcause_full}"
  MANIFEST_ARGS=(
    --manifest research/benchmark_manifests/videomme_dev_v1.toml
    --manifest research/benchmark_manifests/videomme_holdout_v1.toml
  )
else
  echo "MODE must be short or full (got $MODE)" >&2
  exit 2
fi

mkdir -p "$OUT"

run_arm() {
  local name="$1"
  shift
  echo
  echo "=== $name ==="
  "$PY" scripts/run_phase1_30_scaleout_streaming.py \
    "${MANIFEST_ARGS[@]}" \
    --frame-count 8 \
    --max-tokens 32 \
    --model-path "$MODEL_PATH" \
    --rss-guard-mb "$RSS_GUARD_MB" \
    --allow-dirty \
    --output "$OUT/${name}.jsonl" \
    --summary "$OUT/${name}_summary.json" \
    "$@"
}

run_arm cold_dense \
  --stack cold \
  --drift-refresh-policy off \
  --vision-tower-keep-rate 1.0

run_arm cold_pruned \
  --stack cold \
  --drift-refresh-policy off \
  --vision-tower-layer 2 \
  --vision-tower-keep-rate 0.50

run_arm streaming_dense_off \
  --stack streaming \
  --drift-refresh-policy off \
  --vision-tower-keep-rate 1.0

run_arm streaming_pruned_off \
  --stack streaming \
  --drift-refresh-policy off \
  --vision-tower-layer 2 \
  --vision-tower-keep-rate 0.50

run_arm streaming_dense_reset \
  --stack streaming \
  --drift-refresh-policy hard-reset \
  --vision-tower-keep-rate 1.0

run_arm streaming_pruned_reset \
  --stack streaming \
  --drift-refresh-policy hard-reset \
  --vision-tower-layer 2 \
  --vision-tower-keep-rate 0.50

echo
if [[ "$MODE" == "short" ]]; then
  DONE_MODE="SHORT"
else
  DONE_MODE="FULL"
fi
echo "PHASE1_30_ROOTCAUSE_${DONE_MODE}_DONE"
