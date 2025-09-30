PG_DSN=postgresql+asyncpg://postgres:pass@localhost:5433/gym_test


up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f api

bash:
	docker compose exec api bash

db-bash:
	docker compose exec db sh

migrate:
	docker compose exec api alembic upgrade head

rev:
	docker compose exec api alembic revision --autogenerate -m "$(m)"

freshness:
        docker compose exec api python -m scripts.update_freshness

test:
        @TEST_DATABASE_URL=$(PG_DSN) pytest -q

seed-equip:
        python -m scripts.seed --equip-only

# --- Dev tooling ---
pre-commit-install:
	pre-commit install

pre-commit-run:
	pre-commit run --all-files
