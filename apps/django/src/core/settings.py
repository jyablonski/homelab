import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "unsafe-dev-key-change-me")
DEBUG = os.getenv("DJANGO_DEBUG", "false").lower() == "true"
ALLOWED_HOSTS = [
    h.strip() for h in os.getenv("DJANGO_ALLOWED_HOSTS", "*").split(",") if h.strip()
]
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]

USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "core.urls"
WSGI_APPLICATION = "core.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME", "postgres"),
        "USER": os.getenv("DB_USER", "postgres"),
        "PASSWORD": os.getenv("DB_PASSWORD", ""),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
        "OPTIONS": {
            "options": f"-c search_path={os.getenv('DB_SEARCH_PATH', 'source,public')}",
        },
    },
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = os.getenv("TZ", "UTC")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

DJANGO_SSO_ENABLED = os.getenv("DJANGO_SSO_ENABLED", "false").lower() == "true"
DJANGO_OIDC_CLIENT_ID = os.getenv("DJANGO_OIDC_CLIENT_ID", "")
DJANGO_OIDC_CLIENT_SECRET = os.getenv("DJANGO_OIDC_CLIENT_SECRET", "")
DJANGO_OIDC_ISSUER_URL = os.getenv(
    "DJANGO_OIDC_ISSUER_URL",
    "http://authentik-server.authentik.svc.cluster.local/application/o/django/",
)
DJANGO_OIDC_AUTHORIZE_URL = os.getenv(
    "DJANGO_OIDC_AUTHORIZE_URL",
    "http://authentik.home/application/o/authorize/",
)
DJANGO_OIDC_TOKEN_URL = os.getenv(
    "DJANGO_OIDC_TOKEN_URL",
    "http://authentik-server.authentik.svc.cluster.local/application/o/token/",
)
DJANGO_OIDC_USERINFO_URL = os.getenv(
    "DJANGO_OIDC_USERINFO_URL",
    "http://authentik-server.authentik.svc.cluster.local/application/o/userinfo/",
)
DJANGO_OIDC_JWKS_URL = os.getenv(
    "DJANGO_OIDC_JWKS_URL",
    "http://authentik-server.authentik.svc.cluster.local/application/o/django/jwks/",
)
DJANGO_OIDC_SCOPES = os.getenv("DJANGO_OIDC_SCOPES", "openid email profile")
DJANGO_OIDC_CALLBACK_URL = os.getenv(
    "DJANGO_OIDC_CALLBACK_URL",
    "http://django.home/sso/callback/",
)
DJANGO_SSO_STAFF_GROUP = os.getenv("DJANGO_SSO_STAFF_GROUP", "")
DJANGO_SSO_SUPERUSER_GROUP = os.getenv("DJANGO_SSO_SUPERUSER_GROUP", "")
LOGIN_URL = "/sso/login/"
LOGIN_REDIRECT_URL = "/admin/"
