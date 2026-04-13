"""
Clinic LAN settings — runs on the Mac, team connects via WiFi.
Uses SQLite (no PostgreSQL install needed).
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = 'joyvet-clinic-local-secret-key-change-if-needed'
DEBUG = False
ALLOWED_HOSTS = ['*']  # LAN only — safe since not exposed to internet

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'django_filters',
    'corsheaders',
    'channels',
    'django_celery_beat',
    'django_celery_results',
    'apps.core.apps.CoreConfig',
    'apps.clients.apps.ClientsConfig',
    'apps.patients.apps.PatientsConfig',
    'apps.emr.apps.EmrConfig',
    'apps.inventory.apps.InventoryConfig',
    'apps.billing.apps.BillingConfig',
    'apps.appointments.apps.AppointmentsConfig',
    'apps.analytics.apps.AnalyticsConfig',
    'frontend',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.core.middleware.AuditMiddleware',
    'apps.core.middleware.TimezoneMiddleware',
]

ROOT_URLCONF = 'joyvet.urls'
WSGI_APPLICATION = 'joyvet.wsgi.application'
ASGI_APPLICATION = 'joyvet.asgi.application'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.core.context_processors.clinic_context',
            ],
        },
    },
]

# SQLite — no installation needed
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'clinic_data.sqlite3',
    }
}

# In-memory channel layer (real-time still works within single process)
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

# Run Celery tasks immediately (no worker process needed)
CELERY_TASK_ALWAYS_EAGER = True

AUTH_PASSWORD_VALIDATORS = []  # Relaxed for clinic internal use

LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True
CLINIC_TIMEZONE = 'Asia/Jakarta'

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'api.pagination.StandardPagination',
    'PAGE_SIZE': 25,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'EXCEPTION_HANDLER': 'api.exceptions.custom_exception_handler',
}

FILE_UPLOAD_MAX_MEMORY_SIZE = 52_428_800
DATA_UPLOAD_MAX_MEMORY_SIZE = 52_428_800

SECURE_PROXY_SSL_HEADER = None
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
CSRF_COOKIE_HTTPONLY = False

CLINIC_NAME = 'JoyVet Care'
CLINIC_CURRENCY = 'IDR'
INVOICE_PREFIX = 'INV'
LOW_STOCK_ALERT_DAYS = 7
EXPIRY_ALERT_DAYS = [30, 60, 90]
WHATSAPP_ENABLED = False

CORS_ALLOW_ALL_ORIGINS = True

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'root': {'handlers': ['console'], 'level': 'WARNING'},
}
