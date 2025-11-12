## --- Environment loading ---
## ENV_FILE は手動で上書き可: `make ENV_FILE=.env.prod target`
ENV_FILE ?= .env
ifdef APP_ENV
ifeq ($(APP_ENV),prod)
ENV_FILE := .env.prod
endif
endif

## ENV_FILE の変数を取り込む（存在すれば）
ifneq (,$(wildcard $(ENV_FILE)))
include $(ENV_FILE)
## include で読み込んだキーを export（ps: sedで KEY=VAL の KEY を抽出）
export $(shell sed -n 's/^\([A-Za-z_][A-Za-z0-9_]*\)=.*/\1/p' $(ENV_FILE))
endif

## PG_DSN は TEST_DATABASE_URL→DATABASE_URL→最後に開発用DSNの順で決定
PG_DSN ?= $(or $(TEST_DATABASE_URL),$(DATABASE_URL),postgresql+asyncpg://postgres:pass@localhost:5433/gym_test)


up:
	docker compose --env-file $(ENV_FILE) up -d

down:
	docker compose --env-file $(ENV_FILE) down

logs:
	docker compose --env-file $(ENV_FILE) logs -f api

bash:
	docker compose --env-file $(ENV_FILE) exec api bash

db-bash:
	docker compose --env-file $(ENV_FILE) exec db sh

migrate:
	docker compose --env-file $(ENV_FILE) exec api alembic upgrade head

rev:
	docker compose --env-file $(ENV_FILE) exec api alembic revision --autogenerate -m "$(m)"

freshness:
	docker compose --env-file $(ENV_FILE) exec api python -m scripts.update_freshness

test:
	@TEST_DATABASE_URL=$(PG_DSN) pytest -q

seed-equip:
	python -m scripts.seed --equip-only

# --- Dev tooling ---
pre-commit-install:
	pre-commit install

pre-commit-run:
	pre-commit run --all-files

.PHONY: up down logs bash db-bash migrate rev freshness sync-all test seed-equip \
	pre-commit-install pre-commit-run curl-admin-candidates \
	ingest-fetch ingest-parse ingest-normalize ingest-approve \
	ingest-fetch-site-a ingest-parse-site-a ingest-normalize-site-a \
	ingest-fetch-http-site-a-koto ingest-fetch-http-site-a-funabashi \
	ingest-parse-site-a-funabashi ingest-normalize-site-a-funabashi \
	ingest-fetch-ward ingest-parse-ward ingest-normalize-ward \
        ingest-fetch-municipal-koto ingest-parse-municipal-koto \
        ingest-normalize-municipal-koto ingest-fetch-municipal-edogawa \
        ingest-parse-municipal-edogawa ingest-normalize-municipal-edogawa \
        ingest-fetch-municipal-sumida ingest-parse-municipal-sumida \
        ingest-normalize-municipal-sumida ingest-fetch-municipal-chuo \
        ingest-parse-municipal-chuo ingest-normalize-municipal-chuo \
        ingest-fetch-municipal-minato ingest-parse-municipal-minato \
        ingest-normalize-municipal-minato
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

ingest-fetch-ward:
	docker compose --env-file $(ENV_FILE) exec api \
	  python -m scripts.ingest fetch-http \
	    --source $(S) --pref tokyo --city $(C) --limit $(L)

ingest-parse-ward:
	docker compose --env-file $(ENV_FILE) exec api \
	  python -m scripts.ingest parse --source $(S) --limit $(L)

ingest-normalize-ward:
	docker compose --env-file $(ENV_FILE) exec api \
	  python -m scripts.ingest normalize --source $(S) --limit $(L)

ingest-fetch-municipal-koto:
	$(MAKE) ingest-fetch-ward S=municipal_koto C=koto L=100

ingest-parse-municipal-koto:
	$(MAKE) ingest-parse-ward S=municipal_koto L=200

ingest-normalize-municipal-koto:
	$(MAKE) ingest-normalize-ward S=municipal_koto L=200

ingest-fetch-municipal-edogawa:
	$(MAKE) ingest-fetch-ward S=municipal_edogawa C=edogawa L=100

ingest-parse-municipal-edogawa:
	$(MAKE) ingest-parse-ward S=municipal_edogawa L=200

ingest-normalize-municipal-edogawa:
	$(MAKE) ingest-normalize-ward S=municipal_edogawa L=200

ingest-fetch-municipal-sumida:
	$(MAKE) ingest-fetch-ward S=municipal_sumida C=sumida L=100

ingest-parse-municipal-sumida:
	$(MAKE) ingest-parse-ward S=municipal_sumida L=200

ingest-normalize-municipal-sumida:
        $(MAKE) ingest-normalize-ward S=municipal_sumida L=200

ingest-fetch-municipal-chuo:
        $(MAKE) ingest-fetch-ward S=municipal_chuo C=chuo L=100

ingest-parse-municipal-chuo:
        $(MAKE) ingest-parse-ward S=municipal_chuo L=200

ingest-normalize-municipal-chuo:
        $(MAKE) ingest-normalize-ward S=municipal_chuo L=200

ingest-fetch-municipal-minato:
        $(MAKE) ingest-fetch-ward S=municipal_minato C=minato L=100

ingest-parse-municipal-minato:
        $(MAKE) ingest-parse-ward S=municipal_minato L=200

ingest-normalize-municipal-minato:
        $(MAKE) ingest-normalize-ward S=municipal_minato L=200

curl-admin-candidates:
	@echo "# 一覧"
	@curl -s "http://localhost:8000/admin/candidates?status=new&limit=5" | jq
	@echo "# 承認ドライラン"
	@curl -s -X POST \
		"http://localhost:8000/admin/candidates/1/approve" \
		-H "Content-Type: application/json" \
		-d '{"dry_run":true}' | jq

sync-all:
	docker compose --env-file $(ENV_FILE) exec api \
	  python -m scripts.ops.sync_municipal --areas $(AREAS) $(if $(LIMIT),--limit $(LIMIT))
