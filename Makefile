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