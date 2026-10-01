.PHONY: format lint typecheck

format:
	uv run ruff format .

lint:
	uv run ruff check .

typecheck:
	uv run mypy

.PHONY: check
check:
	uv run ruff format --check .
	uv run ruff check .
	uv run mypy
	PYTHONPATH=src uv run python -m unittest discover -s tests -v
