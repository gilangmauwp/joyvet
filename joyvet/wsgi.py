"""WSGI config — fallback for non-ASGI deployments."""
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'joyvet.settings.local')
application = get_wsgi_application()
