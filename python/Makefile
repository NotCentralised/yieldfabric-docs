# YieldFabric Python Port — Makefile
# Common operations for development and testing.

.PHONY: help install install-dev test test-e2e test-coverage clean format lint type-check version

help:
	@echo "YieldFabric Python — Available Commands"
	@echo "========================================"
	@echo ""
	@echo "Development:"
	@echo "  install        Install the package in development mode"
	@echo "  install-dev    Install with development dependencies (pytest, etc.)"
	@echo ""
	@echo "Testing:"
	@echo "  test           Run all tests (pytest; skips E2E if backend is down)"
	@echo "  test-e2e       Run ONLY the localhost E2E flow tests"
	@echo "  test-coverage  Run tests with coverage report (html + term)"
	@echo ""
	@echo "Code Quality:"
	@echo "  format         Format code with black"
	@echo "  lint           Lint code with flake8"
	@echo "  type-check     Type check with mypy"
	@echo "  check-all      Run all code quality checks + tests"
	@echo ""
	@echo "Running:"
	@echo "  setup          Run system bootstrap against scripts/setup.yaml"
	@echo "                 (python -m yieldfabric.cli setup ../scripts/setup.yaml)"
	@echo "  execute FILE=<path>  Execute a commands YAML file"
	@echo ""
	@echo "Utilities:"
	@echo "  clean          Clean build artifacts + pycache"
	@echo "  version        Print version of yieldfabric, python, and key deps"

# ---- Installation ----------------------------------------------------------

install:
	pip install -e .

install-dev:
	pip install -e .[dev]

# ---- Testing ---------------------------------------------------------------

test:
	PYTHONPATH=. pytest

test-e2e:
	PYTHONPATH=. pytest tests/test_e2e/ -v

test-coverage:
	PYTHONPATH=. pytest --cov=yieldfabric --cov-report=html --cov-report=term

# ---- Code quality ----------------------------------------------------------

format:
	black yieldfabric/ tests/

lint:
	flake8 yieldfabric/ tests/

type-check:
	mypy yieldfabric/

check-all: format lint type-check test

# ---- Runtime ---------------------------------------------------------------

# `make setup` bootstraps users, groups, tokens, and assets against the local
# backend using the canonical scripts/setup.yaml. Assumes AUTH_SERVICE_URL and
# PAY_SERVICE_URL are set (defaults: http://localhost:3000 / :3002).
setup:
	PYTHONPATH=. python -m yieldfabric.cli setup ../scripts/setup.yaml

# `make execute FILE=../scripts/commands.yaml` runs an arbitrary command YAML.
execute:
	@test -n "$(FILE)" || (echo "usage: make execute FILE=<path-to-yaml>" && exit 1)
	PYTHONPATH=. python -m yieldfabric.cli execute $(FILE)

# ---- Utilities -------------------------------------------------------------

clean:
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/ .coverage htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

version:
	@python -c "import yieldfabric; print(f'yieldfabric {yieldfabric.__version__}')"
	@python -c "import sys; print(f'Python {sys.version.split()[0]}')"
	@python -c "import requests; print(f'requests {requests.__version__}')"
	@python -c "import yaml; print(f'PyYAML {yaml.__version__}')"
