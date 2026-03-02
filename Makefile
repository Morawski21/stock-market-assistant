.PHONY: setup lint test clean run

setup:
	uv sync
	uv run pre-commit install

lint:
	uv run ruff check .
	uv run ruff format .

test:
	uv run pytest

run:
	PYTHONPATH=src uv run python main.py

clean:
	find . -type d -name __pycache__ | xargs rm -rf
	rm -rf .pytest_cache .ruff_cache
