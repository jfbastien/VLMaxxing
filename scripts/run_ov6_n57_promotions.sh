#!/usr/bin/env bash
# OV-6 N=57 promotions: re-run the strongest N=10 cells at N=57 to confirm.
#
# Two cells from the N=10 sweep are paper-relevant:
#   1. kr=0.7 / layer=2 — three arms hit 0.800 = dense on N=10
#   2. kr=0.5 / layer=8 — codec_residual ties magnitude_norm at 0.700 on N=10
#
# Re-run both cells on N=57 with 4 arms each (magnitude_norm + 3 codec sources).
# ~34 min/arm × 8 arms = ~4.5h sequential. dense N=57 already exists.

set -uo pipefail
trap 'echo "[ov6prom] arm $LAST_ARM failed at $(date -u +%Y-%m-%dT%H:%M:%SZ); continuing"' ERR

cd "$(dirname "$0")/.."

PY="${OV6P_PYTHON:-uv run python}"
MODEL_PATH="${OV6P_MODEL_PATH:-$HOME/models/Qwen2.5-VL-7B-Instruct-4bit}"
SHORT_N57="${OV6P_MANIFEST:-research/benchmark_manifests/videomme_short_present_v1_n57.toml}"
FRAME_COUNT="${OV6P_FRAME_COUNT:-8}"
MAX_TOKENS="${OV6P_MAX_TOKENS:-32}"
OUT_KR="${OV6P_KR_DIR:-research/experiments/2026/artifacts/phase1_51V_ov6_n57_kr070_l2}"
OUT_LY="${OV6P_LY_DIR:-research/experiments/2026/artifacts/phase1_51V_ov6_n57_kr050_l8}"

mkdir -p "$OUT_KR" "$OUT_LY"

LAST_ARM=""
START_TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
echo "[ov6prom] start $START_TS"

run_arm() {
  local out_base="$1"
  local manifest="$2"
  local label="$3"
  shift 3
  local arm_dir="$out_base/$label"
  if [[ -f "$arm_dir/summary.json" ]]; then
    echo "[ov6prom] === arm=$label SKIP (already done) ==="
    return 0
  fi
  mkdir -p "$arm_dir"
  LAST_ARM="$out_base/$label"
  echo "[ov6prom] === arm=$label starting $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  ${PY} scripts/run_phase1_51V.py \
    --manifest "$manifest" \
    --model-path "$MODEL_PATH" \
    --frame-count "$FRAME_COUNT" \
    --max-tokens "$MAX_TOKENS" \
    --output "$arm_dir/results.jsonl" \
    --summary "$arm_dir/summary.json" \
    --allow-dirty \
    "$@" \
    2>&1 | tee "$arm_dir/run.log"
  echo "[ov6prom] === arm=$label done $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
}

# ---- Cell 1: kr=0.7 / layer=2 at N=57 ----
echo "[ov6prom] === Cell 1: kr=0.7 layer=2 N=57 ==="

run_arm "$OUT_KR" "$SHORT_N57" magnitude_norm \
  --vision-tower-layer 2 --vision-tower-keep-rate 0.7 \
  --score-mode magnitude_norm

run_arm "$OUT_KR" "$SHORT_N57" codec_novel_coded \
  --vision-tower-layer 2 --vision-tower-keep-rate 0.7 \
  --score-mode codec_grid --codec-score-source novel_coded

run_arm "$OUT_KR" "$SHORT_N57" codec_motion \
  --vision-tower-layer 2 --vision-tower-keep-rate 0.7 \
  --score-mode codec_grid --codec-score-source motion

run_arm "$OUT_KR" "$SHORT_N57" codec_residual \
  --vision-tower-layer 2 --vision-tower-keep-rate 0.7 \
  --score-mode codec_grid --codec-score-source residual

# ---- Cell 2: kr=0.5 / layer=8 at N=57 ----
echo "[ov6prom] === Cell 2: kr=0.5 layer=8 N=57 ==="

run_arm "$OUT_LY" "$SHORT_N57" magnitude_norm \
  --vision-tower-layer 8 --vision-tower-keep-rate 0.5 \
  --score-mode magnitude_norm

run_arm "$OUT_LY" "$SHORT_N57" codec_novel_coded \
  --vision-tower-layer 8 --vision-tower-keep-rate 0.5 \
  --score-mode codec_grid --codec-score-source novel_coded

run_arm "$OUT_LY" "$SHORT_N57" codec_motion \
  --vision-tower-layer 8 --vision-tower-keep-rate 0.5 \
  --score-mode codec_grid --codec-score-source motion

run_arm "$OUT_LY" "$SHORT_N57" codec_residual \
  --vision-tower-layer 8 --vision-tower-keep-rate 0.5 \
  --score-mode codec_grid --codec-score-source residual

END_TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
echo "[ov6prom] end $END_TS"
