#!/bin/bash
# Build script for Render deployment

set -e

echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Running migrations..."
python manage.py migrate

echo "Ensuring admin superuser exists..."
python manage.py create_render_superuser

echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

echo "Build completed successfully!"
