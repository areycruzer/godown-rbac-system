"""Local development settings."""

from apps.common.logging_config import get_logging_config

from config.env import get_csv

from .base import *  # noqa: F403

DEBUG = True
STRUCTLOG_JSON = False
LOGGING = get_logging_config(json_logs=False)

ALLOWED_HOSTS = get_csv(
    "ALLOWED_HOSTS",
    default="localhost,127.0.0.1,0.0.0.0,testserver,.localhost",
)

# ---------------------------------------------------------------------------
# CORS — allow local frontend dev server by default.
# Override CORS_ALLOWED_ORIGINS in .env for other origins.
# ---------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = get_csv(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:3000,http://127.0.0.1:3000",
)
CORS_ALLOW_CREDENTIALS = True

# =============================================================================
# Dockerless/Service-free Overrides
# Use SQLite & Local Memory for database, cache, channels, and Celery tasks
# to allow running the project without PostgreSQL and Redis services.
# =============================================================================

# Override DATABASES to use local SQLite database file
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Override CACHES to use local-memory backend
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "unique-snowflake",
    }
}

# Override CHANNEL_LAYERS to use in-memory channel layer
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    }
}

# Override Celery to execute tasks synchronously in the same thread
CELERY_TASK_ALWAYS_EAGER = True
CELERY_BROKER_URL = "memory://"
CELERY_RESULT_BACKEND = "cache+memory://"
