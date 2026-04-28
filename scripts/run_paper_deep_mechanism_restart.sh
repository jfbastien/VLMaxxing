#!/usr/bin/env bash
# Restart wrapper for the deep-mechanism queue after the 2026-04-27 IOGPU
# kernel panic. 1.63E (8f + 16f catastrophic + partial 20f) is already
# committed as durable boundary evidence; this wrapper resumes the remaining
# stages and adds the 16f kr-sweep that the 1.63E findings called for.
#
# Sequence (continue-on-failure between top-level invocations):
#   1. deep-mechanism queue --start-at 1.63G   → 1.63G, 1.55K, 1.65, 1.30AF, 1.66
#   2. 1.63H 16f kr-sweep at kr ∈ {0.65, 0.75, 0.85}
#   3. final commit of 1.63H artifacts (queue auto-commit covers stages 1-7)

set -uo pipefail

cd "$(dirname "$0")/.."

PY="${PYTHON:-./.venv/bin/python}"
LOG="${PAPER_RESTART_LOG:-/tmp/claude/paper_restart.log}"

echo "[restart] $(date) — starting deep-mechanism queue from 1.63G"
"$PY" scripts/run_paper_deep_mechanism_queue.py --auto-commit --start-at 1.63G
queue_status=$?
echo "[restart] $(date) — queue exit $queue_status"

echo "[restart] $(date) — starting 1.63H 16f kr-sweep"
bash scripts/run_phase1_63H_16f_kr_sweep.sh
sweep_status=$?
echo "[restart] $(date) — kr-sweep exit $sweep_status"

if [[ $sweep_status -eq 0 ]]; then
  if git diff --quiet -- research/experiments/2026/artifacts/phase1_63H_16f_kr_sweep 2>/dev/null \
     && [[ -z "$(git ls-files --others --exclude-standard research/experiments/2026/artifacts/phase1_63H_16f_kr_sweep 2>/dev/null)" ]]; then
    echo "[restart] no 1.63H artifact changes to commit"
  else
    git add research/experiments/2026/artifacts/phase1_63H_16f_kr_sweep || true
    git commit -m "research(1.63H): land 16f kr-sweep artifacts" || true
  fi
fi

echo "[restart] $(date) — done"
