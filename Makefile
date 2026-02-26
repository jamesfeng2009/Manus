.PHONY: help install dev test lint typecheck clean run api

help:
	@echo "Manus - Available Commands"
	@echo "=========================="
	@echo "install      Create venv and install dependencies"
	@echo "dev          Install development dependencies"
	@echo "test         Run tests"
	@echo "lint         Run linter"
	@echo "typecheck    Run type checker"
	@echo "clean        Clean build files"
	@echo "run          Run the application"
	@echo "api          Run API server"

install:
	@if [ ! -d ".venv" ]; then python3 -m venv .venv; fi
	@.venv/bin/pip install --upgrade pip
	@.venv/bin/pip install -r requirements.txt

dev: install
	@.venv/bin/pip install -e ".[dev]"

test:
	@.venv/bin/pytest tests/ -v

lint:
	@.venv/bin/ruff check manus/

typecheck:
	@.venv/bin/mypy manus/

clean:
	rm -rf build/ dist/ *.egg-info .venv
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

run:
	@.venv/bin/litestar run

api:
	@.venv/bin/litestar run --host 0.0.0.0 --port 8000
