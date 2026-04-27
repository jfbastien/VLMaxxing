#!/usr/bin/env bash
# Phase 1.55K — adaptive C-PERSIST sampler-temperature sweep on the short tranche.
#
# Extends the adaptive 1.55F headline from greedy decoding to a small practical
# sampling range.
# Each arm uses the same sampler for session and baseline, so paired diffs test
# cache-policy sensitivity rather than sampler mismatch.

set -euo pipefail

cd "$(dirname "$0")/.."

PY="${PYTHON:-./.venv/bin/python}"
MODEL_PATH="${MODEL_PATH:-$HOME/models/Qwen2.5-VL-7B-Instruct-4bit}"
RSS_GUARD_MB="${RSS_GUARD_MB:-9000}"
OUT_DIR="${PHASE1_55K_OUT_DIR:-research/experiments/2026/artifacts/phase1_55K_adaptive_temperature_sweep}"
TEMPERATURES="${PHASE1_55K_TEMPERATURES:-0.5 0.7 1.0 1.5}"
VIDEO_IDS="${PHASE1_55K_VIDEO_IDS:-037,100,116,120,158,160,210}"

mkdir -p "$OUT_DIR"

SUMMARY_ARGS=()
REFERENCE_T00="research/experiments/2026/artifacts/phase1_55F_q3_post_q2_state/pair_metrics_k1_n7.json"
if [[ -f "$REFERENCE_T00" && " $TEMPERATURES " != *" 0.0 "* ]]; then
  SUMMARY_ARGS+=(--cell 0.0 "$REFERENCE_T00")
fi

for TEMPERATURE in $TEMPERATURES; do
  TAG="$(printf '%s' "$TEMPERATURE" | tr '.' 'p')"
  CELL_DIR="$OUT_DIR/t${TAG}"
  mkdir -p "$CELL_DIR"

  if [[ -f "$CELL_DIR/session_k1_n7.jsonl" && -f "$CELL_DIR/baseline_k1_n7.jsonl" && -f "$CELL_DIR/summary_k1_n7.json" ]]; then
    echo "[1.55K] reusing T=${TEMPERATURE} outputs in $CELL_DIR"
  else
    if [[ -f "$CELL_DIR/session_k1_n7.jsonl" || -f "$CELL_DIR/baseline_k1_n7.jsonl" || -f "$CELL_DIR/summary_k1_n7.json" ]]; then
      echo "[1.55K] incomplete T=${TEMPERATURE} outputs detected; rerunning"
    fi
    "$PY" scripts/run_kv_selective_reprefill_v2.py \
      --mode both \
      --video-ids "$VIDEO_IDS" \
      --frame-count 20 \
      --max-tokens 32 \
      --reprefill-k 1 \
      --reprefill-k-q2 1 \
      --reprefill-k-q3 0 \
      --q3-cache-source post_q2_repaired \
      --temperature "$TEMPERATURE" \
      --top-p 0.95 \
      --min-p 0.0 \
      --model-path "$MODEL_PATH" \
      --rss-guard-mb "$RSS_GUARD_MB" \
      --output-dir "$CELL_DIR"
  fi

  "$PY" scripts/analyze_selective_reprefill_pairs.py \
    --session-jsonl "$CELL_DIR/session_k1_n7.jsonl" \
    --baseline-jsonl "$CELL_DIR/baseline_k1_n7.jsonl" \
    --output "$CELL_DIR/pair_metrics_k1_n7.json" \
    --paired-queries "$CELL_DIR/paired_queries_k1_n7.jsonl" \
    --label "phase1_55K_adaptive_temperature_${TEMPERATURE}"

  SUMMARY_ARGS+=(--cell "$TEMPERATURE" "$CELL_DIR/pair_metrics_k1_n7.json")
done

"$PY" scripts/summarize_phase1_55k_temperature_sweep.py \
  "${SUMMARY_ARGS[@]}" \
  --output "$OUT_DIR/temperature_sweep_summary.json"
