import os
import sys
from pathlib import Path
from datetime import timedelta
import dotenv
import dj_database_url
import structlog
import django.http.multipartparser
from celery.schedules import crontab

try:
    django.http.multipartparser.MAX_TOTAL_HEADER_SIZE = 52428800
except Exception:
    pass

BASE_DIR = Path(__file__).resolve().parent.parent
dotenv.load_dotenv(BASE_DIR / ".env", encoding="utf-8-sig")

LOGS_DIR = BASE_DIR / "logs"
try:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
except OSError:
    pass

FILE_LOGGING_ENABLED = os.getenv("DJANGO_FILE_LOGGING", "true").lower(
) == "true" and LOGS_DIR.exists() and os.access(LOGS_DIR, os.W_OK)
DEFAULT_LOG_HANDLERS = ["console"] + (["file"] if FILE_LOGGING_ENABLED else [])

THE_ODDS_API_KEY = os.getenv("THE_ODDS_API_KEY")

SECRET_KEY = os.getenv("SECRET_KEY")

if not SECRET_KEY:
    if "test" in sys.argv:
        SECRET_KEY = "test-secret-key"
    else:
        raise ValueError("SECRET_KEY environment variable is required!")

DEBUG = os.getenv("DEBUG", "False").lower() == "true"
RUNNING_IN_DOCKER = os.getenv("RUNNING_IN_DOCKER", "false") == "true"

ALLOWED_HOSTS = [h.strip() for h in os.getenv(
    "ALLOWED_HOSTS", "").split(",") if h.strip()]

if RUNNING_IN_DOCKER:
    ALLOWED_HOSTS.extend(["localhost", "127.0.0.1", "web"])

SERVER_BASE_URL = os.getenv("SERVER_BASE_URL", "http://localhost:8000")

if not DEBUG and not ALLOWED_HOSTS:
    raise ValueError("ALLOWED_HOSTS must be set in production!")


AUTH_USER_MODEL = "authentication.User"

AUTHENTICATION_BACKENDS = [
    "authentication.auth_backend.MultiFieldAuthBackend",
    "django.contrib.auth.backends.ModelBackend",
]

INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "rest_framework.authtoken",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    "django_celery_results",
    "django_cleanup.apps.CleanupConfig",
    "storages",
    "authentication",
    "dashboard",
    "ai",
    "community",
    "support",
    "betting",
]

MIDDLEWARE = [
    "Rai_Backend.middleware.LatencyMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "Rai_Backend.urls"
WSGI_APPLICATION = "Rai_Backend.wsgi.application"
ASGI_APPLICATION = "Rai_Backend.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

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
            ssl_require=not DEBUG,
        )
    }
    DATABASES["default"]["CONN_HEALTH_CHECKS"] = True
    DATABASES["default"].setdefault("OPTIONS", {})
    DATABASES["default"]["OPTIONS"]["connect_timeout"] = 10
    DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = True
else:
    if not DEBUG:
        raise ValueError(
            "Database environment variables must be set in production!")

    db_path = BASE_DIR / \
        ("dbs/db.sqlite3" if RUNNING_IN_DOCKER else "db.sqlite3")
    db_path.parent.mkdir(parents=True, exist_ok=True)

    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": db_path,
        }
    }

REDIS_URL = os.getenv(
    "REDIS_URL",
    "redis://redis:6379/0" if RUNNING_IN_DOCKER else "redis://127.0.0.1:6379/0",
)

CACHE_REDIS_URL = os.getenv(
    "CACHE_REDIS_URL",
    "redis://redis:6379/1" if RUNNING_IN_DOCKER else "redis://127.0.0.1:6379/1",
)

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

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "django-db")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = int(os.getenv("CELERY_TASK_TIME_LIMIT", 300))
CELERY_TASK_SOFT_TIME_LIMIT = int(
    os.getenv("CELERY_TASK_SOFT_TIME_LIMIT", 240))
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_WORKER_PREFETCH_MULTIPLIER = int(
    os.getenv("CELERY_PREFETCH_MULTIPLIER", 1))
CELERY_BROKER_POOL_LIMIT = int(os.getenv("CELERY_BROKER_POOL_LIMIT", 10))
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = os.getenv(
    "CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP", "True").lower() == "true"
CELERY_TASK_ROUTES = {
    "ai.tasks.generate_ai_response": {"queue": "heavy_queue"},
    "*": {"queue": "default"},
}

CELERY_BEAT_SCHEDULE = {
    "flush-expired-tokens-nightly": {
        "task": "authentication.tasks.flush_expired_tokens_task",
        "schedule": crontab(hour=0, minute=0),
    },
    "cleanup-expired-otps-15m": {
        "task": "authentication.tasks.cleanup_expired_otps_task",
        "schedule": crontab(minute='*/15'),
    },
    "sync-odds-every-20-minutes": {
        "task": "betting.tasks.sync_odds_data",
        "schedule": crontab(minute='*/20'),
    },
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

if not DEBUG:
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

CORS_ALLOW_ALL_ORIGINS = os.getenv(
    "CORS_ALLOW_ALL_ORIGINS", "False").lower() == "true"
if not CORS_ALLOW_ALL_ORIGINS:
    CORS_ALLOWED_ORIGINS = [o.strip() for o in os.getenv(
        "CORS_ALLOWED_ORIGINS", "").split(",") if o.strip()]
    if not CORS_ALLOWED_ORIGINS and not DEBUG:
        import warnings
        warnings.warn(
            "CORS_ALLOWED_ORIGINS is empty and CORS_ALLOW_ALL_ORIGINS is False. "
            "All cross-origin requests will be blocked. Set CORS_ALLOWED_ORIGINS in your .env.",
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

DATA_UPLOAD_MAX_MEMORY_SIZE = 104857600
FILE_UPLOAD_MAX_MEMORY_SIZE = 104857600

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "authentication.renderers.CustomJSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
        "rest_framework.parsers.FormParser",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": os.getenv("THROTTLE_ANON", "200/minute"),
        "otp": os.getenv("THROTTLE_OTP", "5/minute"),
        "login": os.getenv("THROTTLE_LOGIN", "10/minute"),
        "media": os.getenv("THROTTLE_MEDIA", "2000/hour"),
        "conversation": os.getenv("THROTTLE_CONVERSATION", "100/hour"),
        "user": os.getenv("THROTTLE_USER", "1000/day"),
        "community": os.getenv("THROTTLE_COMMUNITY", "100/hour"),
    },
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "authentication.exceptions.custom_exception_handler",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": int(os.getenv("PAGE_SIZE", 20)),
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=int(os.getenv('JWT_ACCESS_HOURS', 1))),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=int(os.getenv('JWT_REFRESH_DAYS', 7))),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,
    'JWK_URL': None,
    'LEEWAY': 0,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    'TOKEN_USER_CLASS': 'rest_framework_simplejwt.models.TokenUser',
    'JTI_CLAIM': 'jti',
    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': timedelta(hours=1),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=1),
}

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

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

_shared_processors = [
    structlog.stdlib.add_log_level,
    structlog.stdlib.add_logger_name,
    structlog.processors.TimeStamper(fmt="iso"),
    structlog.processors.StackInfoRenderer(),
    structlog.processors.format_exc_info,
]

if DEBUG:
    _console_renderer = structlog.dev.ConsoleRenderer()
else:
    _console_renderer = structlog.processors.JSONRenderer()

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
            "processor": _console_renderer,
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
        "": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": True,
        },
        "django": {
            "handlers": DEFAULT_LOG_HANDLERS,
            "level": os.getenv("DJANGO_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
        "django.db.backends": {
            "handlers": DEFAULT_LOG_HANDLERS,
            "level": os.getenv("DB_LOG_LEVEL", "WARNING"),
            "propagate": False,
        },
        "django.request": {
            "handlers": DEFAULT_LOG_HANDLERS,
            "level": "ERROR",
            "propagate": False,
        },
        "authentication": {"handlers": DEFAULT_LOG_HANDLERS, "level": "DEBUG" if DEBUG else "INFO", "propagate": False},
        "ai": {"handlers": DEFAULT_LOG_HANDLERS, "level": "DEBUG" if DEBUG else "INFO", "propagate": False},
        "community": {"handlers": DEFAULT_LOG_HANDLERS, "level": "DEBUG" if DEBUG else "INFO", "propagate": False},
        "support": {"handlers": DEFAULT_LOG_HANDLERS, "level": "DEBUG" if DEBUG else "INFO", "propagate": False},
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

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")

SOCIALACCOUNT_EMAIL_VERIFICATION = "none"
SOCIALACCOUNT_EMAIL_REQUIRED = True
SOCIALACCOUNT_QUERY_EMAIL = True
SOCIALACCOUNT_STORE_TOKENS = False
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APP": {
            "client_id": GOOGLE_CLIENT_ID,
            "secret": "",
            "key": "",
        },
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
    }
}

DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "noreply@rai.app")
INFOBIP_BASE_URL = os.getenv("INFOBIP_BASE_URL")
INFOBIP_API_KEY = os.getenv("INFOBIP_API_KEY")
INFOBIP_SENDER_ID = os.getenv("INFOBIP_SENDER_ID")

SPECTACULAR_SETTINGS = {
    "TITLE": "Rai Backend API",
    "DESCRIPTION": "Production Grade API for Rai Application",
    "VERSION": "1.0.0",
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True").lower() == "true"
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
