# ULPF developer commands. On Windows use Git Bash, or run the underlying
# commands directly (see each recipe).

BACKEND_PY = backend/.venv/Scripts/python

.PHONY: help setup backend frontend test test-backend test-frontend migrate compose-up compose-down

help:
	@echo "setup          - create venv + install backend & frontend deps"
	@echo "backend        - run FastAPI dev server (:8000)"
	@echo "frontend       - run Vite dev server (:5173)"
	@echo "test           - run backend + frontend test suites"
	@echo "migrate        - alembic upgrade head"
	@echo "compose-up     - docker compose up --build"
	@echo "compose-down   - docker compose down -v"

setup:
	cd backend && python -m venv .venv && .venv/Scripts/python -m pip install -r requirements.txt
	cd frontend && npm install

backend:
	cd backend && .venv/Scripts/python -m uvicorn app.main:app --reload

frontend:
	cd frontend && npm run dev

test-backend:
	cd backend && .venv/Scripts/python -m pytest

test-frontend:
	cd frontend && npm test

test: test-backend test-frontend

migrate:
	cd backend && .venv/Scripts/alembic upgrade head

compose-up:
	docker compose up --build

compose-down:
	docker compose down -v
