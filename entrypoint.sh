#!/bin/sh

set -e

DB_URL="${DATABASE_URL:-$DATABASE_BASE_URL}"

if echo "$DB_URL" | grep -q "postgre"; then
    echo "Waiting for PostgreSQL..."
    
    DB_HOST=$(echo "$DB_URL" | sed -e 's/.*@\([^:\/]*\).*/\1/')
    DB_PORT=$(echo "$DB_URL" | sed -e 's/.*:\([0-9]*\)\/.*/\1/')
    DB_PORT="${DB_PORT:-5432}"
    
    python -c "
import socket, time
host, port = '$DB_HOST', int('$DB_PORT')
while True:
    try:
        socket.create_connection((host, port), timeout=1)
        break
    except OSError:
        time.sleep(0.5)
"
    echo "PostgreSQL started"
fi

if echo "$@" | grep -q "gunicorn"; then
    echo "Running initialization tasks for Web Container..."
    
    if [ "$RUN_MIGRATIONS" = "true" ]; then
        echo "Applying migrations..."
        python manage.py migrate --noinput

        echo "Collecting static files..."
        python manage.py collectstatic --noinput --clear
    else
        echo "Skipping migrations (RUN_MIGRATIONS is set to false)..."
    fi
fi

exec "$@"