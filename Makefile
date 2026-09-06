.PHONY: setup backend frontend test check

setup:
	./scripts/setup.sh

backend:
	@test -x .venv/bin/python || (echo "Run 'make setup' first" && exit 1)
	.venv/bin/python -m uvicorn tunemorph_backend.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

test:
	.venv/bin/python -m pytest

check:
	.venv/bin/python -m ruff check backend audio-engine tests
	.venv/bin/python -m black --check backend audio-engine tests
	cd frontend && npm run lint && npm run typecheck && npm run format:check
