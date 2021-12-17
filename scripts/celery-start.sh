#! /usr/bin/env sh
# Run migrations
alembic upgrade head

celery -A src.celery_app:app  worker -l INFO beat -l INFO --scheduler src.schedulers:DatabaseScheduler
