install:
	uv sync

run:
	uv run database

database:
	uv run database

build:
	uv build

publish:
	uvx twine check dist/*

package-install:
	uv tool install dist/*.whl

lint:
	uv run ruff check .

.PHONY: install run database build publish package-install lint
