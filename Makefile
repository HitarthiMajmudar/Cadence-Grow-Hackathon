# Market Detective — convenience targets
.PHONY: install generate seed backend frontend test diagnose check clean

install:
	cd backend && python3 -m venv .venv && .venv/bin/pip install -U pip && .venv/bin/pip install -r requirements.txt
	cd frontend && npm install

generate:
	cd backend && .venv/bin/python -m app.data.generator

seed:
	cd backend && .venv/bin/python -m scripts.seed

seed-fresh:
	cd backend && .venv/bin/python -m scripts.seed --fresh

backend:
	cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

test:
	cd backend && .venv/bin/python -m pytest
	cd frontend && npm run test

diagnose:
	cd backend && .venv/bin/python -m scripts.diagnose

check:
	cd backend && .venv/bin/ruff check app scripts tests && .venv/bin/python -m pytest -q
	cd frontend && npm run typecheck && npm run lint && npm run build

clean:
	rm -rf backend/.local_store backend/.pytest_cache frontend/dist
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
