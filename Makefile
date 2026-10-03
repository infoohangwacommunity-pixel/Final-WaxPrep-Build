.PHONY: format lint typecheck test check

format:
	uv run ruff format .

lint:
	uv run ruff check .

typecheck:
	uv run mypy src tests/typecheck_model_client.py

test:
	PYTHONPATH=src uv run python -m unittest discover -s tests -v

check:
	uv run ruff format --check .
	uv run ruff check .
	uv run mypy src tests/typecheck_model_client.py
	PYTHONPATH=src uv run python -m unittest discover -s tests -v
