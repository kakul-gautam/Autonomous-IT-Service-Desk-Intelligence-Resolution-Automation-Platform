"""
WSGI config for config project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application
from django.core.management import call_command

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_wsgi_application()

# Auto-run migrations on startup in production (backup for Render free tier)
if os.getenv('RENDER') == 'true':
    try:
        call_command('migrate', '--noinput', verbosity=0)
    except Exception as e:
        print(f"Migration check: {e}")
