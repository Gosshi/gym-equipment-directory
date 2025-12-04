#!/bin/sh
set -e

# Run migrations
echo "Running database migrations..."
alembic upgrade head

# Exec the container's main process (what's set as CMD)
exec "$@"
