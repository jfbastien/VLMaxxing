#!/usr/bin/env bash
# Stage, review, commit, and push the M5-5b 32f expansion artifacts.
#
# Reduces the Sam handoff to two commands:
#   HF_TOKEN=... bash scripts/run_sam_m5_5b_32f_expansion.sh
#   bash scripts/submit_sam_m5_5b_32f_expansion.sh
#
# Auto-skips the branch switch if already on the target branch. Otherwise it
# fetches origin and bases the handoff branch on origin/main (or tracks an
# existing origin/$BRANCH). Stages the two generated *_32f_n21 artifacts
# explicitly (never -A). Prompts before commit and push so Sam can audit; pass
# --yes to skip the prompts.

set -euo pipefail

cd "$(dirname "$0")/.."

BRANCH="${SAM_M5_5B_BRANCH:-sam/scaleout-m5-32f-expansion-20260501}"
OUT_DIR="${SAM_M5_5B_OUT_DIR:-research/experiments/2026/artifacts/sam_scaleout_m5_20260429}"
JSONL="$OUT_DIR/sam_m5_5b_swa_prefix_snapshot_32f_n21.jsonl"
SUMMARY="$OUT_DIR/sam_m5_5b_swa_prefix_snapshot_32f_n21_summary.json"
ASSUME_YES=0

for arg in "$@"; do
  case "$arg" in
    --yes|-y) ASSUME_YES=1 ;;
    *) echo "[sam-submit] unknown arg: $arg" >&2; exit 2 ;;
  esac
done

if [[ ! -f "$JSONL" || ! -f "$SUMMARY" ]]; then
  echo "[sam-submit] missing artifacts; run scripts/run_sam_m5_5b_32f_expansion.sh first" >&2
  echo "  expected: $JSONL" >&2
  echo "  expected: $SUMMARY" >&2
  exit 2
fi

if ! git diff --cached --quiet; then
  echo "[sam-submit] existing staged changes detected; refusing to mix artifacts" >&2
  echo "[sam-submit] unstage or commit them before rerunning this helper" >&2
  git diff --cached --stat >&2
  exit 2
fi

current_branch="$(git rev-parse --abbrev-ref HEAD)"
if [[ "$current_branch" != "$BRANCH" ]]; then
  git fetch origin main
  if git rev-parse --verify --quiet "$BRANCH" >/dev/null; then
    git switch "$BRANCH"
  elif git rev-parse --verify --quiet "origin/$BRANCH" >/dev/null; then
    git switch --track -c "$BRANCH" "origin/$BRANCH"
  else
    git switch -c "$BRANCH" origin/main
  fi
fi

git add -- "$JSONL" "$SUMMARY"

staged_names="$(git diff --cached --name-only)"
expected_names="$(printf "%s\n%s\n" "$JSONL" "$SUMMARY" | sort)"
actual_names="$(printf "%s\n" "$staged_names" | sort)"
if [[ "$actual_names" != "$expected_names" ]]; then
  echo "[sam-submit] staged file set is not exactly the expected artifacts" >&2
  echo "[sam-submit] expected:" >&2
  printf "  %s\n" "$JSONL" "$SUMMARY" >&2
  echo "[sam-submit] actual:" >&2
  while IFS= read -r staged_name; do
    printf "  %s\n" "$staged_name" >&2
  done <<< "$staged_names"
  exit 2
fi

echo
echo "[sam-submit] staged for $BRANCH:"
git diff --cached --stat
echo

if [[ "$ASSUME_YES" != "1" ]]; then
  read -r -p "[sam-submit] commit and push to origin/$BRANCH? [y/N] " reply
  case "$reply" in
    y|Y|yes|YES) ;;
    *) echo "[sam-submit] aborted; staged changes preserved"; exit 1 ;;
  esac
fi

git commit -m "research(sam): expand 32f prefix snapshot evidence" \
  -m "Run the existing M5-5b SWA-aware prefix-snapshot protocol at 32 frames on the full 7-video x 3-question set. This preserves the prior 9-row artifact and adds a 21-row validation target for the Gemma 26B-A4B 32f result."

git push -u origin "HEAD:$BRANCH"

echo "[sam-submit] pushed origin/$BRANCH"
