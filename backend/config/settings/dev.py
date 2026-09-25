from .base import *  # noqa: F403

DEBUG = True
REFRESH_COOKIE_SECURE = False
STORAGES = {
    **STORAGES,
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
