# Run all CI checks locally
ci: lint format-check test

# Run tests
test:
	uv run pytest

# Run linting
lint:
	uv run ruff check .

# Check code formatting
format-check:
	uv run ruff format --check .

# Auto-fix formatting
format:
	uv run ruff format .

# Auto-fix lint issues
lint-fix:
	uv run ruff check . --fix

# Auto-fix all (lint + format)
fix: lint-fix format
