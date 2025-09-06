from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-me')
DEBUG = os.getenv('DEBUG', '1') == '1'
SIMPLE_PROGRESS_MODE = os.getenv('SIMPLE_PROGRESS_MODE', '0') == '1'

# Hosts and CSRF
if DEBUG:
    ALLOWED_HOSTS = ["*"]
else:
    ALLOWED_HOSTS = [h.strip() for h in os.getenv('ALLOWED_HOSTS', '').split(',') if h.strip()]
    if not ALLOWED_HOSTS:
        # Safe fallback for Fly: allow app domain if provided
        fly_app = os.getenv('FLY_APP_NAME', 'dissertation-lifecycle')
        ALLOWED_HOSTS = [f"{fly_app}.fly.dev", ".fly.dev"]
    # Allow internal health checks from Fly machines (IP hosts). You can disable by setting ALLOW_ALL_HOSTS=0
    if os.getenv('ALLOW_ALL_HOSTS', '1') == '1' and '*' not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append('*')

CSRF_TRUSTED_ORIGINS = [o.strip() for o in os.getenv('CSRF_TRUSTED_ORIGINS', '').split(',') if o.strip()]
if not CSRF_TRUSTED_ORIGINS:
    # Sensible defaults for local dev and Fly
    if DEBUG:
        CSRF_TRUSTED_ORIGINS = [
            "http://127.0.0.1",
            "http://127.0.0.1:8000",
            "http://localhost",
            "http://localhost:8000",
        ]
    else:
        # Common Fly origin (update via env for custom domains)
        CSRF_TRUSTED_ORIGINS = ["https://*.fly.dev"]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'tracker',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'tracker.middleware.RequestLogMiddleware',
]

ROOT_URLCONF = 'dissertation_lifecycle.urls'

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
                'tracker.context.simple_mode',
            ],
        },
    },
]

WSGI_APPLICATION = 'dissertation_lifecycle.wsgi.application'

# Database
def parse_database_url(url: str) -> dict:
    # minimal postgres://user:pass@host:port/db parser
    from urllib.parse import urlparse
    p = urlparse(url)
    if p.scheme.startswith('postgres'):
        return {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': p.path.lstrip('/'),
            'USER': p.username,
            'PASSWORD': p.password,
            'HOST': p.hostname,
            'PORT': p.port or '',
        }
    raise ValueError('Unsupported DATABASE_URL scheme')

if os.getenv('DATABASE_URL'):
    DATABASES = {
        'default': parse_database_url(os.environ['DATABASE_URL'])
    }
else:
    # Prefer volume path for SQLite in containers so migrations done in release_command persist
    sqlite_path = os.getenv('SQLITE_PATH')
    if not sqlite_path:
        sqlite_path = '/data/db.sqlite3' if os.path.isdir('/data') else str(BASE_DIR / 'db.sqlite3')
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': sqlite_path,
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = os.getenv('STATIC_ROOT', str(BASE_DIR / 'staticfiles'))
# Use Django 4.2+ STORAGES setting to configure staticfiles backend (silences deprecation warnings)
STORAGES = {
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

MEDIA_URL = '/media/'
MEDIA_ROOT = os.getenv('UPLOAD_ROOT', str(BASE_DIR / 'uploads'))

# Upload policy (can be overridden via env)
UPLOAD_MAX_BYTES = int(os.getenv('UPLOAD_MAX_BYTES', str(10 * 1024 * 1024)))  # default 10 MB
_default_types = ','.join([
    'application/pdf',
    'image/jpeg', 'image/png', 'image/gif',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/msword',
])
UPLOAD_ALLOWED_TYPES = [t.strip() for t in os.getenv('UPLOAD_ALLOWED_TYPES', _default_types).split(',') if t.strip()]

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Email configuration (defaults to console in DEBUG)
EMAIL_BACKEND = os.getenv(
    'EMAIL_BACKEND',
    'django.core.mail.backends.console.EmailBackend' if DEBUG else 'django.core.mail.backends.smtp.EmailBackend',
)
EMAIL_HOST = os.getenv('EMAIL_HOST', '')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', '1') == '1'
EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL', '0') == '1'
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'no-reply@example.com')

# Optional webhooks for advisor digests/alerts
SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL', '')
TEAMS_WEBHOOK_URL = os.getenv('TEAMS_WEBHOOK_URL', '')
# Optional: limit lines posted to webhooks
WEBHOOK_MAX_LINES = int(os.getenv('WEBHOOK_MAX_LINES', '80'))

# Security in production
if not DEBUG:
    SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', '1') == '1'
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', '86400'))  # 1 day default
    SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv('SECURE_HSTS_INCLUDE_SUBDOMAINS', '1') == '1'
    SECURE_HSTS_PRELOAD = os.getenv('SECURE_HSTS_PRELOAD', '0') == '1'
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    # Allow Fly's internal HTTP health check to pass without HTTPS redirect
    # (SecurityMiddleware respects SECURE_REDIRECT_EXEMPT regexes.)
    SECURE_REDIRECT_EXEMPT = [r'^healthz$']

# Optional Sentry error monitoring
SENTRY_DSN = os.getenv('SENTRY_DSN', '')
if SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[DjangoIntegration()],
            traces_sample_rate=float(os.getenv('SENTRY_TRACES_SAMPLE_RATE', '0.0')),
            send_default_pii=os.getenv('SENTRY_SEND_PII', '0') == '1',
        )
    except Exception:
        # Fail open if Sentry isn't installed or initialization fails
        pass

# Basic logging to stdout
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': os.getenv('LOG_LEVEL', 'INFO'),
    },
}

# Optional S3 storage for media uploads (instead of local volume)
if os.getenv('S3_ENABLED', '0') == '1':
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID', '')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', '')
    AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME', '')
    AWS_S3_REGION_NAME = os.getenv('AWS_S3_REGION_NAME', '') or None
    AWS_S3_ENDPOINT_URL = os.getenv('AWS_S3_ENDPOINT_URL', '') or None
    AWS_S3_SIGNATURE_VERSION = os.getenv('AWS_S3_SIGNATURE_VERSION', '') or None
    AWS_S3_FILE_OVERWRITE = False
    AWS_DEFAULT_ACL = None
    AWS_QUERYSTRING_AUTH = os.getenv('AWS_QUERYSTRING_AUTH', '0') == '1'
    # If custom domain provided, update MEDIA_URL
    _custom_domain = os.getenv('AWS_S3_CUSTOM_DOMAIN', '')
    if _custom_domain:
        MEDIA_URL = f"https://{_custom_domain}/"
