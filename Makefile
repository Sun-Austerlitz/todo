PYTHON ?= $(shell [ -x .venv/bin/python ] && echo .venv/bin/python || echo python3)

.PHONY: install run lint test alembic-revision alembic-upgrade alembic-current

install:
	uv sync

run:
	uvicorn main:app --reload

lint:
	ruff check .

test:
	pytest -q

# Alembic migration commands
alembic-revision:
	$(PYTHON) -m alembic revision --autogenerate -m "$(m)"

alembic-upgrade:
	$(PYTHON) -m alembic upgrade head

alembic-current:
	$(PYTHON) -m alembic current
