from .base import *  # noqa: F403

DEBUG = False
# Postgres in Docker/CI (TEST_DATABASE_URL set); SQLite for a quick local run.
DATABASES = {"default": env.db("TEST_DATABASE_URL", default="sqlite://:memory:")}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
CELERY_TASK_ALWAYS_EAGER = True
CELERY_BROKER_URL = "memory://"
CELERY_BROKER_USE_SSL = None
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
MIDDLEWARE = [m for m in MIDDLEWARE if "whitenoise" not in m]
STORAGES = {
    **STORAGES,
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_THROTTLE_RATES": {"login": "1000/min", "public_tracking": "1000/min"},
}
