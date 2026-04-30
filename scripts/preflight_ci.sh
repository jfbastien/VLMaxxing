#!/usr/bin/env bash
# preflight_ci.sh — run all CI gates locally so cherry-picks don't break the build.
#
# Use this AFTER cherry-picking external commits and BEFORE git push:
#   bash scripts/preflight_ci.sh
#
# Mirrors what GitHub Actions runs: ruff format --check, ruff check, and git diff --check
# for trailing whitespace. Exits non-zero on any failure so a `&&`-chain
# halts before push.
#
# Whitespace check covers all changes since origin/main; if you're working
# off a different upstream, set PREFLIGHT_BASE in the environment, e.g.:
#   PREFLIGHT_BASE=origin/release bash scripts/preflight_ci.sh

set -euo pipefail

PY="${PYTHON:-./.venv/bin/python}"
BASE="${PREFLIGHT_BASE:-origin/main}"

cd "$(dirname "$0")/.."

echo "==> ruff format --check ."
"$PY" -m ruff format --check .

echo "==> ruff check ."
"$PY" -m ruff check .

echo "==> git diff --check $BASE..HEAD"
git diff --check "$BASE..HEAD" || {
  echo "preflight: trailing whitespace or conflict markers in commits since $BASE"
  exit 1
}

echo
echo "preflight_ci: PASS"
