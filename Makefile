# Deployment Builder Test Suite
# Performance-optimized test execution

.PHONY: help test test-unit test-integration test-fast test-slow test-parallel test-performance clean

help: ## Show this help message
	@echo "Deployment Builder Test Suite"
	@echo "============================="
	@echo ""
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

test: ## Run all tests (sequential)
	poetry run pytest tests/ -v

test-unit: ## Run unit tests only (parallel)
	poetry run pytest -m "unit" -v -n auto

test-integration: ## Run integration tests only (parallel)
	poetry run pytest -m "integration" -v -n auto

test-fast: ## Run fast tests only (parallel)
	poetry run pytest -m "fast" -v -n auto

test-slow: ## Run slow tests only (sequential)
	poetry run pytest -m "slow" -v

test-parallel: ## Run all tests in parallel
	poetry run pytest tests/ -v -n auto

test-performance: ## Run performance comparison tests
	poetry run python run_tests.py

test-coverage: ## Run tests with coverage report
	poetry run pytest tests/ --cov=src/deployment_builder --cov-report=html --cov-report=term

test-watch: ## Run tests in watch mode (re-run on file changes)
	poetry run pytest-watch tests/

test-debug: ## Run tests with debug output
	poetry run pytest tests/ -v -s --tb=long

test-verbose: ## Run tests with maximum verbosity
	poetry run pytest tests/ -vv --tb=long --durations=0

clean: ## Clean up test artifacts
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf validation_reports/
	rm -rf temp_*/
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

install-dev: ## Install development dependencies
	poetry install --with dev

format: ## Format code with black
	poetry run black src/ tests/

lint: ## Run linting checks
	poetry run black --check src/ tests/
	poetry run flake8 src/ tests/

# Performance targets
benchmark: ## Run performance benchmarks
	poetry run pytest -m "slow" -v --durations=0

profile: ## Run tests with profiling
	poetry run pytest tests/ --profile

# CI/CD targets
ci-test: ## Run tests for CI/CD (fast, parallel)
	poetry run pytest tests/ -v -n auto --maxfail=3 --tb=short

ci-coverage: ## Run tests with coverage for CI/CD
	poetry run pytest tests/ --cov=src/deployment_builder --cov-report=xml --cov-fail-under=80
