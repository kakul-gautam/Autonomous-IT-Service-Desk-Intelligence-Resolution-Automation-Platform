#!/bin/bash
# Build script for Render deployment

set -e

echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Running migrations..."
python manage.py migrate

echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

echo "Build completed successfully!"
