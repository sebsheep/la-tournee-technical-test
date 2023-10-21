#!/bin/bash

echo "Run migrations"
alembic upgrade head

python -m app.main
