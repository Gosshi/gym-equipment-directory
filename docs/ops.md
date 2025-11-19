# Operations & Deployment Runbook

This document summarizes how to prepare environment variables, boot a production-like stack
with Docker Compose, and run geocoding / freshness maintenance jobs.

## 1. Prepare environment files
1. Copy the templates and edit the secrets:
   ```bash
   cp .env.example .env
   cp .env.prod.example .env.prod
   ```
2. Update both files with the correct PostgreSQL credentials, `DATABASE_URL`, external
   service API keys, and tokens such as `ADMIN_UI_TOKEN`.
3. Keep `COMPOSE_ENV_FILE=.env` (for local) or `COMPOSE_ENV_FILE=.env.prod` (for production)
   so that `docker-compose.yml` knows which file to mount inside the containers.

## 2. Boot a production-like stack locally
1. Start the stack with the production env file:
   ```bash
   docker compose --env-file .env.prod up -d
   ```
2. Run database migrations if needed:
   ```bash
   docker compose --env-file .env.prod exec api alembic upgrade head
   ```
3. Validate the API health endpoint:
   ```bash
   curl http://localhost:${APP_PORT:-8080}/healthz
   ```
4. Tail the FastAPI logs for additional verification:
   ```bash
   docker compose --env-file .env.prod logs -f api
   ```

## 3. Operational jobs (geocoding & freshness)
Execute the CLI utilities inside the API container after the stack is online.

```bash
# Geocode gyms missing latitude/longitude from scraped sources.
docker compose --env-file .env.prod exec api \
  python -m scripts.tools.geocode_missing \
    --target gyms \
    --origin scraped

# Update cached freshness timestamps used by search scoring.
docker compose --env-file .env.prod exec api \
  python -m scripts.update_freshness
```

The same commands work for `.env` by replacing `.env.prod` and ensuring the corresponding env
file contains `DATABASE_URL` and `OPENCAGE_API_KEY`.

## 4. Render deployment blueprint
Render-specific configuration lives in [`infra/render.yaml`](../infra/render.yaml).
To launch a new service:

1. Visit [https://dashboard.render.com/](https://dashboard.render.com/) and create a new Web
   Service from the GitHub repository.
2. When prompted for configuration, choose "Use existing render.yaml" and point to
   `infra/render.yaml`.
3. Fill in each secret listed in the `envVars` section (e.g. `DATABASE_URL`,
   `OPENCAGE_API_KEY`, `ADMIN_UI_TOKEN`).
4. Render uses `/healthz` for health checks, so confirm the endpoint returns HTTP 200 locally
   before enabling automatic deploys.

## 5. Quick reference commands
- `docker compose --env-file .env.prod up -d`
- `docker compose --env-file .env.prod exec api python -m scripts.tools.geocode_missing --target gyms --origin scraped`
- `docker compose --env-file .env.prod exec api python -m scripts.update_freshness`
- `curl http://localhost:${APP_PORT:-8080}/healthz`

## 6. Shutdown & cleanup
```bash
docker compose --env-file .env.prod down
```
This stops the containers while leaving persistent PostgreSQL volumes intact.
