#!/usr/bin/env bash
# Render.com build script — runs once on each deploy
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate --no-input
