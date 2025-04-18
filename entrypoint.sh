#!/bin/bash

# Wait for database if needed (commented out for now)
# echo "Waiting for database..."
# while ! nc -z db 5432; do
#   sleep 0.1
# done

cd /app/src/web

# Run database migrations
echo "Running database migrations..."
python manage.py migrate

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --no-input --clear

# Start application
echo "Starting application..."
exec gunicorn --bind 0.0.0.0:8000 web.wsgi:application 