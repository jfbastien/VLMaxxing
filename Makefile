.PHONY: fmt lint test typecheck check

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
