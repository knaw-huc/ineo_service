#!/usr/bin/env sh

cd /app || exit
export FLASK_APP=app
export FLASK_ENV=development
export FLASK_RUN_PORT=8000
gunicorn app:app --bind 0.0.0.0:8000 --reload --timeout 120 --workers 4
