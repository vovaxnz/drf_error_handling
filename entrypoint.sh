#!/bin/sh

python manage.py migrate
python manage.py seed_db
python manage.py collectstatic --noinput

exec gunicorn config.wsgi:application --bind 0.0.0.0:8000