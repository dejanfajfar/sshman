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

# Build pip package (wheel and sdist)
build:
	rm -rf dist/
	uv run python -m build
	@echo ""
	@echo "Built packages:"
	@ls -lh dist/

# Show venv activation instructions
[unix]
venv:
	@echo "Run: source .venv/bin/activate"
	@echo "Or:  source \$(just _venv-path)"

[windows]
venv:
	@echo "Run: .venv\\Scripts\\activate"

# Output venv activate path (for scripting)
[unix]
_venv-path:
	@echo ".venv/bin/activate"

[windows]
_venv-path:
	@echo ".venv\\Scripts\\Activate.ps1"
