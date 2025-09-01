from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-me')
DEBUG = os.getenv('DEBUG', '1') == '1'

# Hosts and CSRF
if DEBUG:
    ALLOWED_HOSTS = ["*"]
else:
    ALLOWED_HOSTS = [h.strip() for h in os.getenv('ALLOWED_HOSTS', '').split(',') if h.strip()]
    if not ALLOWED_HOSTS:
        # Safe fallback for Fly: allow app domain if provided
        fly_app = os.getenv('FLY_APP_NAME', 'dissertation-lifecycle')
        ALLOWED_HOSTS = [f"{fly_app}.fly.dev", ".fly.dev"]

CSRF_TRUSTED_ORIGINS = [o.strip() for o in os.getenv('CSRF_TRUSTED_ORIGINS', '').split(',') if o.strip()]
if not CSRF_TRUSTED_ORIGINS:
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

DATABASES = {
    'default': parse_database_url(os.environ['DATABASE_URL']) if os.getenv('DATABASE_URL') else {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
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
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.getenv('UPLOAD_ROOT', str(BASE_DIR / 'uploads'))

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

# Security in production
if not DEBUG:
    SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', '1') == '1'
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', '86400'))  # 1 day default
    SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv('SECURE_HSTS_INCLUDE_SUBDOMAINS', '1') == '1'
    SECURE_HSTS_PRELOAD = os.getenv('SECURE_HSTS_PRELOAD', '0') == '1'
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
