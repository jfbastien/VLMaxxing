#!/usr/bin/env bash
# OV-6 Track B full M3 sweep: N=57 replication + kr sweep + layer sweep.
#
# Phase A — N=57 replication at kr=0.5 layer=2 (6 arms × 57 items):
#   confirms the N=10 smoke at higher N. ETA ~3.5h.
#
# Phase B — keep_rate sweep at layer=2, N=10 (4 arms × 3 keep-rates = 12 runs):
#   tests if any kr exposes a codec-favorable window. ETA ~1.2h.
#
# Phase C — layer sweep at kr=0.5, N=10 (4 arms × 3 layers = 12 runs):
#   tests if codec helps at deeper layers. ETA ~1.2h.
#
# Total ~6 hours sequential on M3 16GB. Each arm writes to its own subdir so
# partial-restart after a failed arm is trivial.

set -uo pipefail
trap 'echo "[ov6sweep] arm $LAST_ARM failed at $(date -u +%Y-%m-%dT%H:%M:%SZ); continuing"' ERR

cd "$(dirname "$0")/.."

PY="${OV6_PYTHON:-uv run python}"
MODEL_PATH="${OV6_MODEL_PATH:-$HOME/models/Qwen2.5-VL-7B-Instruct-4bit}"
SHORT_N10="${OV6_MANIFEST_N10:-research/benchmark_manifests/videomme_dev_v1_short_only.toml}"
SHORT_N57="${OV6_MANIFEST_N57:-research/benchmark_manifests/videomme_short_present_v1_n57.toml}"
FRAME_COUNT="${OV6_FRAME_COUNT:-8}"
MAX_TOKENS="${OV6_MAX_TOKENS:-32}"
OUT_REP="${OV6_REP_DIR:-research/experiments/2026/artifacts/phase1_51V_ov6_n57}"
OUT_KR="${OV6_KR_DIR:-research/experiments/2026/artifacts/phase1_51V_ov6_kr_sweep}"
OUT_LY="${OV6_LY_DIR:-research/experiments/2026/artifacts/phase1_51V_ov6_layer_sweep}"

mkdir -p "$OUT_REP" "$OUT_KR" "$OUT_LY"

LAST_ARM=""
START_TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
echo "[ov6sweep] start $START_TS"
echo "[ov6sweep] phases: replication(n=57), kr_sweep(n=10), layer_sweep(n=10)"

# ---- helper: runs one arm if its summary.json doesn't already exist ----
run_arm() {
  local out_base="$1"
  local manifest="$2"
  local label="$3"
  shift 3
  local arm_dir="$out_base/$label"
  if [[ -f "$arm_dir/summary.json" ]]; then
    echo "[ov6sweep] === arm=$label SKIP (already done) ==="
    return 0
  fi
  mkdir -p "$arm_dir"
  LAST_ARM="$out_base/$label"
  echo "[ov6sweep] === arm=$label starting $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
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
  echo "[ov6sweep] === arm=$label done $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
}

# ---- Phase A: N=57 replication at kr=0.5 layer=2 ----
echo "[ov6sweep] === Phase A: N=57 replication ==="

run_arm "$OUT_REP" "$SHORT_N57" dense \
  --vision-tower-keep-rate 1.0

run_arm "$OUT_REP" "$SHORT_N57" magnitude_norm_kr050 \
  --vision-tower-layer 2 --vision-tower-keep-rate 0.5 \
  --score-mode magnitude_norm

run_arm "$OUT_REP" "$SHORT_N57" uniform_random_kr050 \
  --vision-tower-layer 2 --vision-tower-keep-rate 0.5 \
  --score-mode uniform_random

run_arm "$OUT_REP" "$SHORT_N57" codec_novel_coded_kr050 \
  --vision-tower-layer 2 --vision-tower-keep-rate 0.5 \
  --score-mode codec_grid --codec-score-source novel_coded

run_arm "$OUT_REP" "$SHORT_N57" codec_motion_kr050 \
  --vision-tower-layer 2 --vision-tower-keep-rate 0.5 \
  --score-mode codec_grid --codec-score-source motion

run_arm "$OUT_REP" "$SHORT_N57" codec_residual_kr050 \
  --vision-tower-layer 2 --vision-tower-keep-rate 0.5 \
  --score-mode codec_grid --codec-score-source residual

# ---- Phase B: keep_rate sweep at layer=2, N=10 ----
echo "[ov6sweep] === Phase B: kr sweep N=10 ==="

for KR in 0.30 0.70 0.90; do
  KR_TAG=$(printf "%03d" "$(echo "$KR * 100" | bc | awk '{printf "%d", $0}')")
  run_arm "$OUT_KR" "$SHORT_N10" "magnitude_norm_kr${KR_TAG}" \
    --vision-tower-layer 2 --vision-tower-keep-rate "$KR" \
    --score-mode magnitude_norm

  run_arm "$OUT_KR" "$SHORT_N10" "codec_novel_coded_kr${KR_TAG}" \
    --vision-tower-layer 2 --vision-tower-keep-rate "$KR" \
    --score-mode codec_grid --codec-score-source novel_coded

  run_arm "$OUT_KR" "$SHORT_N10" "codec_motion_kr${KR_TAG}" \
    --vision-tower-layer 2 --vision-tower-keep-rate "$KR" \
    --score-mode codec_grid --codec-score-source motion

  run_arm "$OUT_KR" "$SHORT_N10" "codec_residual_kr${KR_TAG}" \
    --vision-tower-layer 2 --vision-tower-keep-rate "$KR" \
    --score-mode codec_grid --codec-score-source residual
done

# ---- Phase C: layer sweep at kr=0.5, N=10 ----
echo "[ov6sweep] === Phase C: layer sweep N=10 ==="

for LAYER in 1 4 8; do
  run_arm "$OUT_LY" "$SHORT_N10" "magnitude_norm_l${LAYER}" \
    --vision-tower-layer "$LAYER" --vision-tower-keep-rate 0.5 \
    --score-mode magnitude_norm

  run_arm "$OUT_LY" "$SHORT_N10" "codec_novel_coded_l${LAYER}" \
    --vision-tower-layer "$LAYER" --vision-tower-keep-rate 0.5 \
    --score-mode codec_grid --codec-score-source novel_coded

  run_arm "$OUT_LY" "$SHORT_N10" "codec_motion_l${LAYER}" \
    --vision-tower-layer "$LAYER" --vision-tower-keep-rate 0.5 \
    --score-mode codec_grid --codec-score-source motion

  run_arm "$OUT_LY" "$SHORT_N10" "codec_residual_l${LAYER}" \
    --vision-tower-layer "$LAYER" --vision-tower-keep-rate 0.5 \
    --score-mode codec_grid --codec-score-source residual
done

END_TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
echo "[ov6sweep] end $END_TS"
