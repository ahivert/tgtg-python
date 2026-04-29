test:
	uv run --all-extras pytest

lint:
	uv run --all-extras ruff check .
	uv run --all-extras ruff format --check .

publish:
	uv build && uv publish
