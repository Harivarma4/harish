.DEFAULT_GOAL := help
PY ?= python

.PHONY: help setup lint typecheck security test check run docker-build docker-up clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

setup: ## Install the package with dev dependencies
	$(PY) -m pip install -e ".[dev]"

lint: ## Run ruff linter
	ruff check src tests

typecheck: ## Run mypy static type checker
	mypy

security: ## Run bandit security scanner
	bandit -q -r src

test: ## Run the test suite
	pytest

check: lint typecheck security test ## Run the full DevSecOps gate

run: ## Start the API locally (reload)
	uvicorn atlas_ai.api.main:app --reload --host 0.0.0.0 --port 8000 --app-dir src

docker-build: ## Build the container image
	docker build -t atlas-ai:local .

docker-up: ## Start the stack via docker compose
	docker compose up --build

clean: ## Remove caches and build artifacts
	rm -rf .pytest_cache .mypy_cache .ruff_cache build dist src/*.egg-info
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
