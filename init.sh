#!/bin/bash
set -e

echo "Run migrations"
alembic upgrade head

python -m app.main
