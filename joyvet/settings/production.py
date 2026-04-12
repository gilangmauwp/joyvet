"""
Production settings for JoyVet Care clinic server.
Accessed via LAN: https://192.168.1.100 or https://joyvet.local
"""
from decouple import config, Csv
from .base import *  # noqa: F401, F403

DEBUG = False

ALLOWED_HOSTS: list[str] = config(
    'ALLOWED_HOSTS',
    default='192.168.1.100,joyvet.local',
    cast=Csv(),
)

# Security hardening (LAN-safe subset — no HSTS redirect loops)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# CORS — restrict to LAN origins only
CORS_ALLOWED_ORIGINS: list[str] = config(
    'CORS_ALLOWED_ORIGINS',
    default='https://192.168.1.100,https://joyvet.local',
    cast=Csv(),
)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {'handlers': ['console'], 'level': 'WARNING'},
    'loggers': {
        'django': {'handlers': ['console'], 'level': 'WARNING', 'propagate': False},
        'apps':   {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
        'celery': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
    },
}
