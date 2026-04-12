"""
JoyVet Care — Base Django Settings
Environment-specific overrides go in local.py / production.py
"""
from pathlib import Path
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY: str = config('SECRET_KEY', default='django-insecure-change-in-production')

INSTALLED_APPS = [
    # Daphne MUST come before staticfiles for ASGI
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third-party
    'rest_framework',
    'rest_framework_simplejwt',
    'django_filters',
    'corsheaders',
    'channels',
    'django_celery_beat',
    'django_celery_results',
    # Local apps — using app labels (no 'apps.' prefix confusion in migrations)
    'apps.core.apps.CoreConfig',
    'apps.clients.apps.ClientsConfig',
    'apps.patients.apps.PatientsConfig',
    'apps.emr.apps.EmrConfig',
    'apps.inventory.apps.InventoryConfig',
    'apps.billing.apps.BillingConfig',
    'apps.appointments.apps.AppointmentsConfig',
    'apps.analytics.apps.AnalyticsConfig',
    # HTMX frontend
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
ASGI_APPLICATION = 'joyvet.asgi.application'
WSGI_APPLICATION = 'joyvet.wsgi.application'

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

# ── Database ───────────────────────────────────────────────
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='joyvet'),
        'USER': config('DB_USER', default='joyvet'),
        'PASSWORD': config('DB_PASSWORD', default='joyvetpass'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
        'CONN_MAX_AGE': 60,
        'OPTIONS': {'connect_timeout': 10},
    }
}

# ── Cache (Redis) ──────────────────────────────────────────
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': config('REDIS_URL', default='redis://localhost:6379/1'),
        'TIMEOUT': 300,
    }
}

# ── Django Channels / WebSockets ───────────────────────────
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [config('REDIS_URL', default='redis://localhost:6379/0')],
            'capacity': 1500,
            'expiry': 10,
        },
    },
}

# ── Celery ─────────────────────────────────────────────────
CELERY_BROKER_URL: str = config('REDIS_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = 'django-db'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
CELERY_TASK_TRACK_STARTED = True

# ── Auth ───────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

# ── Internationalisation ───────────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True
CLINIC_TIMEZONE = 'Asia/Jakarta'  # WIB — for display only

# ── Static & Media ─────────────────────────────────────────
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── Django REST Framework ──────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework_simplejwt.authentication.JWTAuthentication',
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
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'user': '1000/hour',
        'search': '200/minute',
    },
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'EXCEPTION_HANDLER': 'api.exceptions.custom_exception_handler',
}

# ── File upload limits ─────────────────────────────────────
FILE_UPLOAD_MAX_MEMORY_SIZE = 52_428_800   # 50 MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 52_428_800

# ── Security headers ───────────────────────────────────────
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False   # HTMX reads CSRF from cookie

# ── Clinic / business settings ─────────────────────────────
CLINIC_NAME: str = config('CLINIC_NAME', default='JoyVet Care')
CLINIC_CURRENCY = 'IDR'
INVOICE_PREFIX: str = config('INVOICE_PREFIX', default='INV')
LOW_STOCK_ALERT_DAYS: int = 7
EXPIRY_ALERT_DAYS: list[int] = [30, 60, 90]

# ── WhatsApp (optional) ────────────────────────────────────
WHATSAPP_ENABLED: bool = bool(config('TWILIO_ACCOUNT_SID', default=''))
WHATSAPP_PROVIDER: str = config('WHATSAPP_PROVIDER', default='twilio')
TWILIO_ACCOUNT_SID: str = config('TWILIO_ACCOUNT_SID', default='')
TWILIO_AUTH_TOKEN: str = config('TWILIO_AUTH_TOKEN', default='')
TWILIO_WHATSAPP_FROM: str = config('TWILIO_WHATSAPP_FROM', default='')
DIALOG360_API_KEY: str = config('DIALOG360_API_KEY', default='')
