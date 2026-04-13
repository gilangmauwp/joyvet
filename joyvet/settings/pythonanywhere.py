"""
PythonAnywhere free-tier settings.
Free plan: SQLite DB, WSGI (no WebSockets), whitenoise static files.
"""
import os
from .base import *  # noqa: F401, F403

DEBUG = False

# Remove daphne — PythonAnywhere uses WSGI, daphne would try to bind a port
INSTALLED_APPS = [app for app in INSTALLED_APPS if app != 'daphne']  # noqa: F405

# PythonAnywhere username — set via environment variable
PA_USERNAME = os.environ.get('PA_USERNAME', 'joyvet')

ALLOWED_HOSTS = [
    f'{PA_USERNAME.lower()}.pythonanywhere.com',
    f'{PA_USERNAME}.pythonanywhere.com',
    'localhost',
    '127.0.0.1',
]

# ── Database — SQLite (free tier, no PostgreSQL needed) ─────
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),  # noqa: F405
    }
}

# ── No Redis on free tier — use in-memory fallbacks ────────
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Disable Celery (no background workers on free tier)
CELERY_TASK_ALWAYS_EAGER = True

# ── Static files — WhiteNoise serves them ──────────────────
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')  # noqa: F405

# ── Security ────────────────────────────────────────────────
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
CSRF_TRUSTED_ORIGINS = [f'https://{PA_USERNAME.lower()}.pythonanywhere.com']
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
    },
    'root': {'handlers': ['console'], 'level': 'WARNING'},
}
