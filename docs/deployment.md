# Deployment Guide

This document describes the deployment architecture and process for the Gym Equipment Directory application.

## Architecture

- **Backend**: Hosted on [Render](https://render.com).
    - **Service Type**: Web Service (Docker)
    - **Database**: PostgreSQL (Managed by Render or external provider)
    - **Cron Jobs**: Background worker for nightly ingestion.
- **Frontend**: Hosted on [Vercel](https://vercel.com).
    - **Framework**: Next.js

## Backend Deployment (Render)

The backend is containerized using Docker.

### Configuration (`render.yaml`)
The project includes a `render.yaml` Blueprint specification.
- **Web Service**: Runs the FastAPI application (`uvicorn`).
- **Cron Job**: Runs the ingestion script (`scripts.ingest.run_nightly`) daily.

### Dockerfile
The production Dockerfile is located at `backend/Dockerfile.render`.
- **Multi-stage build**: Uses `builder` and `runner` stages to minimize image size.
- **Entrypoint**: `backend/entrypoint.sh` is used to automatically run database migrations (`alembic upgrade head`) before starting the application.

### Environment Variables
The following environment variables must be set in Render:

| Variable | Description |
|---|---|
| `DATABASE_URL` | Connection string for PostgreSQL. |
| `OPENAI_API_KEY` | API key for OpenAI (used for address cleaning/extraction). |
| `GOOGLE_MAPS_API_KEY` | API key for Google Maps (Geocoding). |
| `SENTRY_DSN` | DSN for Sentry error tracking. |
| `LOG_FORMAT` | Set to `json` for production logging. |
| `DISCORD_WEBHOOK_URL` | Webhook URL for cost reports and notifications. |

## Frontend Deployment (Vercel)

The frontend is a Next.js application located in the `frontend/` directory.

### Configuration
- **Framework Preset**: Next.js
- **Root Directory**: `frontend`
- **Build Command**: `npm run build` or `next build`
- **Output Directory**: `.next`

### Environment Variables
| Variable | Description |
|---|---|
| `NEXT_PUBLIC_API_URL` | URL of the backend API (e.g., `https://gym-backend.onrender.com`). |

## CI/CD

### GitHub Actions
- **CI (`.github/workflows/ci.yml`)**: Runs on every Push to `main` and Pull Request.
    - Runs `ruff` (linting/formatting).
    - Runs `pytest` (unit tests).
- **Deployment**:
    - **Render**: Connected to the GitHub repository. Deploys automatically on push to `main`.
    - **Vercel**: Connected to the GitHub repository. Deploys automatically on push to `main`.
