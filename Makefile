.PHONY: help setup lint test run clean

help:
	@echo "Available commands:"
	@echo "  make setup   install dependencies and pre-commit hooks"
	@echo "  make lint    run ruff check and format"
	@echo "  make test    run pytest"
	@echo "  make run     start the CLI chat"
	@echo "  make clean   remove cache directories"

setup:
	uv sync
	uv run pre-commit install

lint:
	uv run ruff check .
	uv run ruff format .

test:
	uv run pytest

run:
	uv run python main.py

clean:
	uv run python scripts/clean.py
