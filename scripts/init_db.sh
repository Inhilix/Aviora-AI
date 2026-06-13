#!/bin/bash
# Run inside the fastapi container after first deploy
set -e

echo "Running Alembic migrations..."
cd /app
alembic upgrade head

echo "Database initialised."
