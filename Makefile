.PHONY: fmt lint test typecheck check paper-doctor paper-sync paper-build paper-bundle

PAPER_PYTHON ?= ./.venv/bin/python

fmt:
	uv run ruff format .

lint:
	uv run ruff check .

test:
	uv run pytest

typecheck:
	uv run mypy src tests

check:
	uv run ruff format --check .
	uv run ruff check .
	uv run mypy src tests
	uv run pytest
	uv run python scripts/audit_artifact_integrity.py

paper-doctor:
	$(PAPER_PYTHON) paper/arxiv/scripts/doctor.py

paper-sync:
	$(PAPER_PYTHON) paper/arxiv/scripts/sync_sources.py

paper-build: paper-doctor
	$(PAPER_PYTHON) paper/arxiv/scripts/build.py

paper-bundle:
	$(PAPER_PYTHON) paper/arxiv/scripts/build.py --skip-pdf --bundle
