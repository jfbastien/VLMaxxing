#!/usr/bin/env bash
# Sam M5-5b 32f expansion.
#
# Expands the existing 32f prefix-snapshot result from 9 rows to the full
# 7-video x 3-question shape. Requires HF_TOKEN and Sam's M5 environment.

set -euo pipefail

cd "$(dirname "$0")/.."

PY="${PYTHON:-python3}"
OUT_DIR="${SAM_M5_5B_OUT_DIR:-research/experiments/2026/artifacts/sam_scaleout_m5_20260429}"
OUT_JSONL="${SAM_M5_5B_32F_OUT:-$OUT_DIR/sam_m5_5b_swa_prefix_snapshot_32f_n21.jsonl}"
SUMMARY_JSON="${SAM_M5_5B_32F_SUMMARY:-$OUT_DIR/sam_m5_5b_swa_prefix_snapshot_32f_n21_summary.json}"
N_VIDEOS="${SAM_M5_5B_N_VIDEOS:-7}"
N_FRAMES="${SAM_M5_5B_N_FRAMES:-32}"

if [[ -z "${HF_TOKEN:-}" ]]; then
  echo "[sam-m5-5b-32f] HF_TOKEN is required" >&2
  exit 2
fi

mkdir -p "$OUT_DIR"

"$PY" scripts/run_sam_m5_5b_swa_prefix_snapshot.py \
  --n-videos "$N_VIDEOS" \
  --n-frames "$N_FRAMES" \
  --single-shot-prefill \
  --out "$OUT_JSONL"

"$PY" scripts/validate_sam_scaleout_artifact.py \
  --jsonl "$OUT_JSONL" \
  --phase M5-5b \
  --min-rows 21 \
  --require-zero-choice-diffs \
  --require-zero-correctness-diffs \
  --require-zero-parse-failures \
  --require-matching-prompt-hash \
  --require-matching-frame-hashes \
  --require-positive-prefix-on-followups \
  --summary-output "$SUMMARY_JSON"

bash scripts/preflight_ci.sh

echo "[sam-m5-5b-32f] wrote $OUT_JSONL"
echo "[sam-m5-5b-32f] wrote $SUMMARY_JSON"
