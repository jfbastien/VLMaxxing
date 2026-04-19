#!/usr/bin/env bash
# Back-to-back MLX experiment runner — autonomous /loop queue.
#
# Runs all MLX-gated experiments sequentially, logs each result, and
# writes a final summary JSON. Designed to be launched once in the
# background; no prompts, no pauses.
#
# Usage: bash scripts/run_loop_experiments.sh
#
# Each experiment writes its own artifact dir + log. Failures are
# captured but do NOT abort the queue — we want the rest of the
# work to run while the user is AFK.

set -u  # undefined var = error, but NOT -e (keep queue running on per-step failure)

REPO="/Users/jfb/s/codec-through"
cd "$REPO" || exit 2

QUEUE_DIR="$REPO/research/experiments/2026/artifacts/loop_queue_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$QUEUE_DIR"
MANIFEST="$QUEUE_DIR/manifest.json"
SUMMARY="$QUEUE_DIR/summary.md"
ERROR_LOG="$QUEUE_DIR/errors.log"

echo "[loop] queue dir: $QUEUE_DIR" | tee -a "$SUMMARY"
echo "[loop] started: $(date -Iseconds)" | tee -a "$SUMMARY"

PY="$REPO/.venv/bin/python3"
if [[ ! -x "$PY" ]]; then
  echo "[loop] ERROR: $PY not executable" | tee -a "$ERROR_LOG"
  exit 3
fi

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
run_step() {
  local name="$1"
  shift
  local log="$QUEUE_DIR/${name}.log"
  local t0=$(date +%s)
  echo "" | tee -a "$SUMMARY"
  echo "=== $name — start $(date -Iseconds) ===" | tee -a "$SUMMARY"
  echo "cmd: $*" | tee -a "$log"
  # shellcheck disable=SC2068
  "$@" >>"$log" 2>&1
  local rc=$?
  local t1=$(date +%s)
  local dt=$((t1 - t0))
  if [[ $rc -eq 0 ]]; then
    echo "  [OK] $name in ${dt}s" | tee -a "$SUMMARY"
  else
    echo "  [FAIL rc=$rc] $name in ${dt}s (see $log)" | tee -a "$SUMMARY" | tee -a "$ERROR_LOG"
  fi
  echo "$name rc=$rc dt=${dt}s" >>"$MANIFEST"
}

# ---------------------------------------------------------------------------
# Experiment 1 — Phase 1.55A persistent-KV session (Qwen 7B-4bit)
#   Prereg: 2026-04-19-phase-1_55A-persistent-kv-reproduction-prereg.md
#   Scope:  7 short-bucket clips × 3 questions each, both modes.
#   H1-H4:  computed in-script.
# ---------------------------------------------------------------------------
run_step "1_55A_persistent_kv" \
  "$PY" "$REPO/scripts/run_kv_cache_session.py" \
    --mode both \
    --output-dir "$QUEUE_DIR/phase1_55A_persistent_kv_qwen"

# ---------------------------------------------------------------------------
# Experiment 2 — Phase 1.57 Qwen validation re-run (smoke, n=5) at 8f
#   Sanity check that measure_feature_drift.py still works post-refactor.
# ---------------------------------------------------------------------------
mkdir -p "$QUEUE_DIR/phase1_57"
run_step "1_57_qwen_short_8f_smoke" \
  "$PY" "$REPO/scripts/measure_feature_drift.py" \
    --model qwen \
    --manifest "$REPO/research/benchmark_manifests/videomme_dev_v1.toml" \
    --group short \
    --frame-count 8 \
    --output "$QUEUE_DIR/phase1_57/qwen_8f_short_smoke.json"

# ---------------------------------------------------------------------------
# (Dropped) Experiment 3 — 1.58 bf16 load smoke
#   The mlx-community/Qwen2.5-VL-7B-Instruct (bf16) repo does not exist
#   under that id, and the full 1.58 prereg already flags bf16 as DEFERRED
#   pending a valid 15 GB checkpoint. Dropped from the queue.

# ---------------------------------------------------------------------------
# Final summary
# ---------------------------------------------------------------------------
echo "" | tee -a "$SUMMARY"
echo "=== QUEUE COMPLETE $(date -Iseconds) ===" | tee -a "$SUMMARY"
echo "queue dir: $QUEUE_DIR" | tee -a "$SUMMARY"
echo "manifest:  $MANIFEST" | tee -a "$SUMMARY"
if [[ -s "$ERROR_LOG" ]]; then
  echo "errors:    $ERROR_LOG ($(wc -l < "$ERROR_LOG") lines)" | tee -a "$SUMMARY"
else
  echo "errors:    none" | tee -a "$SUMMARY"
fi
echo "DONE marker: $QUEUE_DIR/DONE" | tee -a "$SUMMARY"
touch "$QUEUE_DIR/DONE"
