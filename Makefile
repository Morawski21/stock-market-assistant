.PHONY: setup lint test clean

setup:
	uv sync
	uv run pre-commit install

lint:
	uv run ruff check .
	uv run ruff format .

test:
	uv run pytest

clean:
	find . -type d -name __pycache__ | xargs rm -rf
	rm -rf .pytest_cache .ruff_cache
