# YieldFabric Python Port Makefile
# Common operations for development and testing

.PHONY: help install install-dev test clean format lint type-check example test-install

# Default target
help:
	@echo "YieldFabric Python Port - Available Commands"
	@echo "============================================="
	@echo ""
	@echo "Development:"
	@echo "  install        Install the package in development mode"
	@echo "  install-dev    Install with development dependencies"
	@echo "  install-enhanced Install with enhanced features"
	@echo ""
	@echo "Testing:"
	@echo "  test           Run all tests"
	@echo "  test-install   Test installation and basic functionality"
	@echo "  test-coverage  Run tests with coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  format         Format code with black"
	@echo "  lint           Lint code with flake8"
	@echo "  type-check     Type check with mypy"
	@echo "  check-all      Run all code quality checks"
	@echo ""
	@echo "Examples:"
	@echo "  example        Run example usage script"
	@echo "  example-help   Show help for the Python port"
	@echo ""
	@echo "Utilities:"
	@echo "  clean          Clean build artifacts"
	@echo "  requirements   Update requirements.txt"
	@echo "  help           Show this help message"

# Installation targets
install:
	pip install -e .

install-dev:
	pip install -e .[dev]

install-enhanced:
	pip install -e .[enhanced]

# Testing targets
test:
	pytest

test-install:
	python test_installation.py

test-coverage:
	pytest --cov=yieldfabric --cov-report=html --cov-report=term

# Code quality targets
format:
	black yieldfabric/ *.py

lint:
	flake8 yieldfabric/ *.py

type-check:
	mypy yieldfabric/ *.py

check-all: format lint type-check test

# Example targets
example:
	python example_usage.py

example-help:
	python -m yieldfabric.main help

# Utility targets
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

requirements:
	pip freeze > requirements.txt

# Development workflow
dev-setup: install-dev
	@echo "Development environment set up successfully!"
	@echo "Run 'make test-install' to verify installation"

# Quick test without full test suite
quick-test: test-install
	@echo "Quick test completed!"

# Full development check
dev-check: check-all test-install
	@echo "All development checks passed!"

# Show version info
version:
	@python -c "import yieldfabric; print('YieldFabric Python Port')"
	@python -c "import sys; print(f'Python {sys.version}')"
	@python -c "import requests; print(f'requests {requests.__version__}')"
	@python -c "import yaml; print(f'PyYAML available')"
