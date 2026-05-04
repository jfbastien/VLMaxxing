#!/usr/bin/env bash
# preflight_ci.sh — run all CI gates locally so cherry-picks don't break the build.
#
# Use this AFTER cherry-picking external commits and BEFORE git push:
#   bash scripts/preflight_ci.sh
#
# Mirrors the CPU-safe repository checks: format, lint, type-check, unit tests,
# artifact integrity, generated paper assets, and whitespace checks. The CI
# paper job also builds the extracted arXiv bundle in Docker.
#
# Whitespace check covers all changes since origin/main; if you're working
# off a different upstream, set PREFLIGHT_BASE in the environment, e.g.:
#   PREFLIGHT_BASE=origin/release bash scripts/preflight_ci.sh

set -euo pipefail

BASE="${PREFLIGHT_BASE:-origin/main}"

cd "$(dirname "$0")/.."

echo "==> ruff format --check ."
uv run ruff format --check .

echo "==> ruff check ."
uv run ruff check .

echo "==> mypy src tests"
uv run mypy src tests

echo "==> pytest"
uv run pytest

echo "==> artifact integrity"
uv run python scripts/audit_artifact_integrity.py

echo "==> paper sync"
uv run python paper/arxiv/scripts/sync_sources.py

echo "==> generated paper asset diff"
git diff --exit-code -- paper/arxiv/generated paper/figures
if [ -n "$(git status --porcelain -- paper/arxiv/generated paper/figures)" ]; then
  git status --short -- paper/arxiv/generated paper/figures
  echo "preflight: untracked or modified generated paper assets"
  exit 1
fi

echo "==> git diff --check $BASE..HEAD"
git diff --check "$BASE..HEAD" || {
  echo "preflight: trailing whitespace or conflict markers in commits since $BASE"
  exit 1
}

echo
echo "preflight_ci: PASS"
