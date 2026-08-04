.PHONY: bootstrap check python-check web-check local-up local-down

bootstrap:
	python -m venv .venv
	.venv/bin/python -m pip install --upgrade "pip>=25,<26.2"
	.venv/bin/python -m pip install --constraint requirements/development.txt -e ".[dev]"
	pnpm install --frozen-lockfile

python-check:
	.venv/bin/ruff format --check services packages/governance-core scripts
	.venv/bin/ruff check services packages/governance-core scripts
	.venv/bin/mypy
	.venv/bin/pytest --cov --cov-report=term-missing
	.venv/bin/python scripts/quality/validate_repository.py

web-check:
	pnpm check:web

check: python-check web-check

local-up:
	docker compose up --build

local-down:
	docker compose down
