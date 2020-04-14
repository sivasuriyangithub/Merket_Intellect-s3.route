"""
With these settings, tests run faster.
"""

from .base import *  # noqa
from .base import env

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = False
# https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default="MJjHQ9lF8AMyhaIWOOogNsH23QQJ53fX3x01uXPfFODMX3rYiuKde0C6QrDV6ZD1",
)
# https://docs.djangoproject.com/en/dev/ref/settings/#test-runner
TEST_RUNNER = "django.test.runner.DiscoverRunner"

MEDIA_URL = f"https://storage.googleapis.com/test/media/"
MEDIA_ROOT = f"https://storage.googleapis.com/test/media/"

# CACHES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#caches
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "",
    }
}

CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default=CELERY_BROKER_URL)
CELERY_REDIS_SOCKET_CONNECT_TIMEOUT = 1.0
CELERY_REDIS_SOCKET_TIMEOUT = 3.0

# PASSWORDS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#password-hashers
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# TEMPLATES
# ------------------------------------------------------------------------------
TEMPLATES[0]["OPTIONS"]["loaders"] = [  # noqa F405
    (
        "django.template.loaders.cached.Loader",
        [
            "django.template.loaders.filesystem.Loader",
            "django.template.loaders.app_directories.Loader",
        ],
    )
]

# EMAIL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Your stuff...
# ------------------------------------------------------------------------------
COLD_EMAIL_KEY = "COLD_EMAIL_KEY"
COLD_ROUTER_API_KEY = "COLD_ROUTER_API_KEY"
DATAVALIDATION_KEY = "DATAVALIDATION_KEY"
COLD_EMAIL_WHOIS = "123"
COLD_EMAIL_PROFILEID = "456"
COLD_EMAIL_SUPRESSIONLIST = "1"
