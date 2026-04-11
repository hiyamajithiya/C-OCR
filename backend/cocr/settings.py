"""
Django settings for C-OCR project.
Migrated from FastAPI (app/core/config.py).
"""

import json
from pathlib import Path
import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

# --- Core ---
SECRET_KEY = env("JWT_SECRET", default="django-insecure-change-me")
DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1", "0.0.0.0"])

# --- Database ---
USE_SQLITE = env.bool("USE_SQLITE", default=False)
if USE_SQLITE:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    # Prefer explicit DB_* settings when present so local credentials/ports are respected.
    db_name = env("DB_NAME", default="")
    db_user = env("DB_USER", default="")
    db_password = env("DB_PASSWORD", default="")
    db_host = env("DB_HOST", default="")
    db_port = env("DB_PORT", default="")

    if any([db_name, db_user, db_password, db_host, db_port]):
        DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": db_name or "c_ocr",
                "USER": db_user or "postgres",
                "PASSWORD": db_password or "postgres",
                "HOST": db_host or "localhost",
                "PORT": db_port or "5432",
            }
        }
    else:
        DATABASES = {
            "default": env.db(
                "DATABASE_URL",
                default="postgresql://postgres:postgres@localhost:5432/c_ocr",
            ),
        }

# --- Installed Apps ---
INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "accounts",
    "documents",
    "templates_app",
    "extractions",
    "api_keys",
    "audit",
    "corrections",
    "external_api",
    "entities",
]

# --- Middleware ---
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "core.middleware.RequestIDMiddleware",
    "core.middleware.RateLimitHeadersMiddleware",
]

ROOT_URLCONF = "cocr.urls"
WSGI_APPLICATION = "cocr.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
            ],
        },
    },
]

# --- CORS ---
_cors_raw = env("CORS_ORIGINS", default='["http://localhost:3000", "http://localhost:8000"]')
if isinstance(_cors_raw, str):
    try:
        CORS_ALLOWED_ORIGINS = json.loads(_cors_raw)
    except json.JSONDecodeError:
        CORS_ALLOWED_ORIGINS = [o.strip() for o in _cors_raw.split(",")]
else:
    CORS_ALLOWED_ORIGINS = _cors_raw
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOW_HEADERS = [
    "accept", "accept-encoding", "authorization", "content-type",
    "origin", "user-agent", "x-api-key", "x-csrftoken", "x-request-id",
]
CORS_ALLOW_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]

# --- DRF ---
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "core.authentication.JWTBearerAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "core.permissions.IsActiveUser",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ],
    "EXCEPTION_HANDLER": "core.exceptions.custom_exception_handler",
    "UNAUTHENTICATED_USER": None,
    "DEFAULT_THROTTLE_RATES": {
        "anon": "30/min",
        "user": "120/min",
        "login": "5/min",
        "document_upload": "30/hour",
    },
}

# --- i18n / tz ---
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = False
USE_TZ = False

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

# --- JWT ---
JWT_SECRET = env("JWT_SECRET", default="your-secret-key-change-this-in-production")
JWT_ALGORITHM = env("JWT_ALGORITHM", default="HS256")
JWT_EXPIRATION_MINUTES = env.int("JWT_EXPIRATION_MINUTES", default=1440)

# --- API Key ---
API_KEY_HASH_SALT = env("API_KEY_HASH_SALT", default="your-salt-change-this-in-production")

# --- Redis / Celery ---
REDIS_URL = env("REDIS_URL", default="redis://localhost:6379/0")
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="redis://localhost:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
CELERY_TASK_TIME_LIMIT = 3600
CELERY_TASK_SOFT_TIME_LIMIT = 3300

# --- Storage ---
STORAGE_PATH = env("STORAGE_PATH", default="./storage")
UPLOAD_MAX_SIZE = env.int("UPLOAD_MAX_SIZE", default=52428800)

# --- OCR ---
OCR_ENGINE_PRIMARY = env("OCR_ENGINE_PRIMARY", default="paddle")
OCR_ENGINE_FALLBACK = env("OCR_ENGINE_FALLBACK", default="tesseract")
OCR_LANGS = env("OCR_LANGS", default="en")
DEFAULT_DPI = env.int("DEFAULT_DPI", default=300)

# --- Template ---
TEMPLATE_MATCH_THRESHOLD = env.float("TEMPLATE_MATCH_THRESHOLD", default=0.75)

# --- Server ---
API_HOST = env("API_HOST", default="0.0.0.0")
API_PORT = env.int("API_PORT", default=8000)
WORKERS = env.int("WORKERS", default=4)

# --- Multi-tenancy ---
MULTI_TENANT_MODE = env.bool("MULTI_TENANT_MODE", default=True)
DEFAULT_TENANT_NAME = env("DEFAULT_TENANT_NAME", default="Default Tenant")

# --- Rate Limiting ---
RATE_LIMIT_PER_MINUTE = env.int("RATE_LIMIT_PER_MINUTE", default=60)
RATE_LIMIT_DAILY_QUOTA = env.int("RATE_LIMIT_DAILY_QUOTA", default=1000)

# --- Logging ---
LOG_LEVEL = env("LOG_LEVEL", default="INFO")
LOG_FORMAT = env("LOG_FORMAT", default="json")

# --- Environment ---
ENVIRONMENT = env("ENVIRONMENT", default="development")

# --- Project Info ---
PROJECT_NAME = "C-OCR"
VERSION = "1.0.0"
DESCRIPTION = "OCR + Template-based Data Extraction Platform"
