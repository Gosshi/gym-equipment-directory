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

.PHONY: ingest-fetch ingest-parse ingest-normalize ingest-approve \
        ingest-fetch-site-a ingest-parse-site-a ingest-normalize-site-a \
        ingest-fetch-http-site-a-koto ingest-fetch-http-site-a-funabashi \
        ingest-parse-site-a-funabashi ingest-normalize-site-a-funabashi
ingest-fetch:
        python -m scripts.ingest fetch --source dummy --limit 10
ingest-parse:
        python -m scripts.ingest parse --source dummy --limit 10
ingest-normalize:
        python -m scripts.ingest normalize --source dummy --limit 10
ingest-approve:
        python -m scripts.ingest approve --candidate-id 1 --dry-run

ingest-fetch-site-a:
        python -m scripts.ingest fetch --source site_a --limit 10
ingest-fetch-http-site-a-koto:
        python -m scripts.ingest fetch-http \
                --source site_a \
                --pref tokyo \
                --city koto \
                --limit 10 \
                --min-delay 2 \
                --max-delay 4
ingest-fetch-http-site-a-funabashi:
        python -m scripts.ingest fetch-http \
                --source site_a \
                --pref chiba \
                --city funabashi \
                --limit 10 \
                --min-delay 2 \
                --max-delay 4
ingest-parse-site-a:
        python -m scripts.ingest parse --source site_a --limit 10
ingest-parse-site-a-funabashi:
        python -m scripts.ingest parse --source site_a --limit 10
ingest-normalize-site-a:
        python -m scripts.ingest normalize --source site_a --limit 10
ingest-normalize-site-a-funabashi:
        python -m scripts.ingest normalize --source site_a --limit 10

curl-admin-candidates:
        @echo "# 一覧"
        @curl -s "http://localhost:8000/admin/candidates?status=new&limit=5" | jq
        @echo "# 承認ドライラン"
        @curl -s -X POST \
                "http://localhost:8000/admin/candidates/1/approve" \
                -H "Content-Type: application/json" \
                -d '{"dry_run":true}' | jq
