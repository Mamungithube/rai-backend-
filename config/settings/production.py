import os
import dj_database_url
import structlog
from .base import *

DEBUG = False

ALLOWED_HOSTS = [h.strip() for h in os.getenv("ALLOWED_HOSTS", "").split(",") if h.strip()]
if RUNNING_IN_DOCKER:
    ALLOWED_HOSTS.extend(["localhost", "127.0.0.1", "web", "testserver"])

if not ALLOWED_HOSTS:
    raise ValueError("ALLOWED_HOSTS must be set in production!")

# Database: PostgreSQL with PgBouncer
DB_NAME = os.getenv("DB_NAME")
DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("DATABASE_BASE_URL")

if DB_NAME and os.getenv("DB_USER") and os.getenv("DB_PASSWORD"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": DB_NAME,
            "USER": os.getenv("DB_USER"),
            "PASSWORD": os.getenv("DB_PASSWORD"),
            "HOST": os.getenv("DB_HOST", "pgbouncer"),
            "PORT": os.getenv("DB_PORT", "5432"),
            "CONN_MAX_AGE": int(os.getenv("DB_CONN_MAX_AGE", 60)),
        }
    }
    DATABASES["default"]["CONN_HEALTH_CHECKS"] = True
    DATABASES["default"].setdefault("OPTIONS", {})
    DATABASES["default"]["OPTIONS"]["connect_timeout"] = 10
    DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = True
elif DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=int(os.getenv("DB_CONN_MAX_AGE", 60)),
            ssl_require=True,
        )
    }
    DATABASES["default"]["CONN_HEALTH_CHECKS"] = True
    DATABASES["default"].setdefault("OPTIONS", {})
    DATABASES["default"]["OPTIONS"]["connect_timeout"] = 10
    DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = True
else:
    raise ValueError("Database environment variables (DB_NAME or DATABASE_URL) must be set in production!")

# Redis & Channels
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": CACHE_REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "IGNORE_EXCEPTIONS": False,
        },
        "TIMEOUT": int(os.getenv("CACHE_DEFAULT_TIMEOUT", 300)),
        "KEY_PREFIX": os.getenv("CACHE_KEY_PREFIX", "rai"),
    }
}

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [CACHE_REDIS_URL],
            "expiry": int(os.getenv("CHANNEL_EXPIRY", 900)),
        },
    }
}

# Strict Security Headers
SECURE_SSL_REDIRECT = os.getenv("REQUIRE_SSL", "True").lower() == "true"
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
X_FRAME_OPTIONS = "DENY"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_REFERRER_POLICY = "same-origin"

# CORS & CSRF
CORS_ALLOW_ALL_ORIGINS = os.getenv("CORS_ALLOW_ALL_ORIGINS", "False").lower() == "true"
if not CORS_ALLOW_ALL_ORIGINS:
    CORS_ALLOWED_ORIGINS = [o.strip() for o in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",") if o.strip()]
    if not CORS_ALLOWED_ORIGINS:
        import warnings
        warnings.warn(
            "CORS_ALLOWED_ORIGINS is empty and CORS_ALLOW_ALL_ORIGINS is False in production.",
            stacklevel=2
        )

CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()
]
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = (
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
    "ngrok-skip-browser-warning",
)

# S3 vs WhiteNoise Storage
USE_AWS = os.getenv("USE_AWS", "False").lower() == "true"
if USE_AWS:
    AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME")
    AWS_S3_REGION_NAME = os.getenv("AWS_S3_REGION_NAME")
    AWS_S3_CUSTOM_DOMAIN = f"{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com"
    STATIC_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/static/"
    MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/media/"
    STORAGES = {
        "default": {"BACKEND": "storages.backends.s3boto3.S3Boto3Storage", "OPTIONS": {"location": "media"}},
        "staticfiles": {"BACKEND": "storages.backends.s3boto3.S3Boto3Storage", "OPTIONS": {"location": "static"}},
    }
else:
    STATIC_URL = "/static/"
    STATIC_ROOT = BASE_DIR / "staticfiles"
    MEDIA_URL = "/media/"
    MEDIA_ROOT = BASE_DIR / "media"
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
    }

# Production Logging: Structured JSON & Rotating Files
FILE_LOGGING_ENABLED = os.getenv("DJANGO_FILE_LOGGING", "true").lower() == "true" and LOGS_DIR.exists() and os.access(LOGS_DIR, os.W_OK)
DEFAULT_LOG_HANDLERS = ["console"] + (["file"] if FILE_LOGGING_ENABLED else [])

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
_shared_processors = [
    structlog.stdlib.add_log_level,
    structlog.stdlib.add_logger_name,
    structlog.processors.TimeStamper(fmt="iso"),
    structlog.processors.StackInfoRenderer(),
    structlog.processors.format_exc_info,
]

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        *_shared_processors,
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "structured": {
            "()": structlog.stdlib.ProcessorFormatter,
            "processor": structlog.processors.JSONRenderer(),
            "foreign_pre_chain": _shared_processors,
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "structured",
        },
    },
    "loggers": {
        "": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": True},
        "django": {"handlers": DEFAULT_LOG_HANDLERS, "level": os.getenv("DJANGO_LOG_LEVEL", "INFO"), "propagate": False},
        "django.db.backends": {"handlers": DEFAULT_LOG_HANDLERS, "level": os.getenv("DB_LOG_LEVEL", "WARNING"), "propagate": False},
        "django.request": {"handlers": DEFAULT_LOG_HANDLERS, "level": "ERROR", "propagate": False},
        "authentication": {"handlers": DEFAULT_LOG_HANDLERS, "level": "INFO", "propagate": False},
        "ai": {"handlers": DEFAULT_LOG_HANDLERS, "level": "INFO", "propagate": False},
        "community": {"handlers": DEFAULT_LOG_HANDLERS, "level": "INFO", "propagate": False},
        "support": {"handlers": DEFAULT_LOG_HANDLERS, "level": "INFO", "propagate": False},
        "celery": {"handlers": DEFAULT_LOG_HANDLERS, "level": "INFO", "propagate": False},
    },
}

if FILE_LOGGING_ENABLED:
    LOGGING["handlers"]["file"] = {
        "level": "INFO",
        "class": "logging.handlers.RotatingFileHandler",
        "filename": LOGS_DIR / "django.log",
        "formatter": "structured",
        "maxBytes": 10485760,
        "backupCount": 5,
    }
