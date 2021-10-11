import logging

import sentry_sdk
from google.auth import compute_engine
from google.cloud import logging as stackdriver
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.logging import LoggingIntegration, ignore_logger
from sentry_sdk.integrations.redis import RedisIntegration

from .base import *  # noqa
from .base import env

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
SECRET_KEY = env("DJANGO_SECRET_KEY")
# https://docs.djangoproject.com/en/dev/ref/settings/#allowed-hosts
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["whoknows.com",])
USE_X_FORWARDED_HOST = True
CSRF_TRUSTED_ORIGINS = ALLOWED_HOSTS

# DATABASES
# ------------------------------------------------------------------------------
DATABASES["default"]["CONN_MAX_AGE"] = env.int("CONN_MAX_AGE", default=60)  # noqa F405

# CACHES
# ------------------------------------------------------------------------------
REDIS_URL = env("REDIS_URL", default=None)
if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": REDIS_URL,
            "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
            "LOCATION": "/app/django_cache",
        }
    }

# SECURITY
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-proxy-ssl-header
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-ssl-redirect
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
# https://docs.djangoproject.com/en/dev/ref/settings/#session-cookie-secure
SESSION_COOKIE_SECURE = True
# https://docs.djangoproject.com/en/dev/ref/settings/#csrf-cookie-secure
CSRF_COOKIE_SECURE = True
# https://docs.djangoproject.com/en/dev/topics/security/#ssl-https
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-hsts-seconds
# TODO: set this to 60 seconds first and then to 518400 once you prove the former works
SECURE_HSTS_SECONDS = 60
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-hsts-include-subdomains
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool(
    "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True
)
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-hsts-preload
SECURE_HSTS_PRELOAD = env.bool("DJANGO_SECURE_HSTS_PRELOAD", default=True)
# https://docs.djangoproject.com/en/dev/ref/middleware/#x-content-type-options-nosniff
SECURE_CONTENT_TYPE_NOSNIFF = env.bool(
    "DJANGO_SECURE_CONTENT_TYPE_NOSNIFF", default=True
)

# STORAGES
# ------------------------------------------------------------------------------
# https://django-storages.readthedocs.io/en/latest/#installation
INSTALLED_APPS += ["storages"]  # noqa F405
DEFAULT_FILE_STORAGE = "storages.backends.gcloud.GoogleCloudStorage"
GS_BUCKET_NAME = env("DJANGO_GCP_STORAGE_BUCKET_NAME")
GS_DEFAULT_ACL = "publicRead"
# STATIC
# ------------------------
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
# MEDIA
# ------------------------------------------------------------------------------
MEDIA_URL = f"https://storage.googleapis.com/{GS_BUCKET_NAME}/media/"
MEDIA_ROOT = f"https://storage.googleapis.com/{GS_BUCKET_NAME}/media/"

# TEMPLATES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#templates
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
# https://docs.djangoproject.com/en/dev/ref/settings/#default-from-email
DEFAULT_FROM_EMAIL = env(
    "DJANGO_DEFAULT_FROM_EMAIL", default="WhoKnows <team@whoknows.com>"
)
# https://docs.djangoproject.com/en/dev/ref/settings/#server-email
SERVER_EMAIL = env("DJANGO_SERVER_EMAIL", default=DEFAULT_FROM_EMAIL)
# https://docs.djangoproject.com/en/dev/ref/settings/#email-subject-prefix
EMAIL_SUBJECT_PREFIX = env("DJANGO_EMAIL_SUBJECT_PREFIX", default="[WhoWeb] ")

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_USE_SSL = True
EMAIL_PORT = 465  # 587 if EMAIL_USE_TLS
EMAIL_HOST_USER = "team@whoknows.com"
EMAIL_HOST_PASSWORD = env("SMTP_PASSWORD")

# ADMIN
# ------------------------------------------------------------------------------
# Django Admin URL regex.
ADMIN_URL = env("DJANGO_ADMIN_URL", default="admin/")

# Anymail (Mailgun)
# ------------------------------------------------------------------------------
# https://anymail.readthedocs.io/en/stable/installation/#installing-anymail
# INSTALLED_APPS += ["anymail"]  # noqa F405
# EMAIL_BACKEND = "anymail.backends.mailgun.EmailBackend"
# # https://anymail.readthedocs.io/en/stable/installation/#anymail-settings-reference
# ANYMAIL = {
#     "MAILGUN_API_KEY": env("MAILGUN_API_KEY"),
#     "MAILGUN_SENDER_DOMAIN": env("MAILGUN_DOMAIN"),
#     "MAILGUN_API_URL": env("MAILGUN_API_URL", default="https://api.mailgun.net/v3"),
# }

# WhiteNoise
# ------------------------------------------------------------------------------
# http://whitenoise.evans.io/en/latest/django.html#enable-whitenoise
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")  # noqa F405

# LOGGING
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#logging
# See https://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.

# StackDriver setup
credentials = compute_engine.Credentials()
client = stackdriver.Client(
    credentials=credentials, project=env.str("GCP_PROJECT", default="wkinfra-171623")
)
# LOGGING = {
#     "version": 1,
#     "disable_existing_loggers": False,
#     "handlers": {
#         "stackdriver_logging": {
#             "class": "google.cloud.logging.handlers.CloudLoggingHandler",
#             "client": client,
#         },
#         "sentry_breadcrumbs": {
#             "level": "INFO",
#             "class": "sentry_sdk.integrations.logging.BreadcrumbHandler",
#         },
#         "sentry_logging": {
#             "level": "ERROR",
#             "class": "sentry_sdk.integrations.logging.EventHandler",
#         },
#     },
#     "loggers": {
#         "django": {
#             "handlers": ["stackdriver_logging", "sentry_breadcrumbs", "sentry_logging"],
#             "level": "DEBUG",
#             "propagate": True,
#         },
#         "django.request": {
#             "handlers": ["stackdriver_logging", "sentry_breadcrumbs", "sentry_logging"],
#             "level": "ERROR",
#         },
#         # Errors logged by the SDK itself
#         "sentry_sdk": {"level": "ERROR", "handlers": ["stackdriver_logging"]},
#     },
# }
LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "formatters": {
        "verbose": {
            "format": "%(levelname)s %(asctime)s %(module)s "
            "%(process)d %(thread)d %(message)s"
        },
        "json": {"()": "whoweb.contrib.logging.DjangoJsonFormatter",},
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "json",
        }
    },
    "root": {"level": "INFO", "handlers": ["console"]},
    "loggers": {
        "django.request": {
            "handlers": ["console"],
            "level": env("DJANGO_LOG_LEVEL", default="INFO"),
            "propagate": False,
        },
        "django.db.backends": {
            "level": "ERROR",
            "handlers": ["console"],
            "propagate": False,
        },
        # Errors logged by the SDK itself
        "sentry_sdk": {"level": "ERROR", "handlers": ["console"], "propagate": False},
        "django.security.DisallowedHost": {
            "level": "ERROR",
            "handlers": ["console"],
            "propagate": False,
        },
    },
}

# Sentry
# ------------------------------------------------------------------------------
SENTRY_DSN = env("SENTRY_DSN")
SENTRY_LOG_LEVEL = env.int("DJANGO_SENTRY_LOG_LEVEL", logging.INFO)

sentry_logging = LoggingIntegration(
    level=SENTRY_LOG_LEVEL,  # Capture info and above as breadcrumbs
    event_level=logging.ERROR,  # Send errors as events
)
sentry_sdk.init(
    dsn=SENTRY_DSN,
    integrations=[
        sentry_logging,
        DjangoIntegration(),
        CeleryIntegration(),
        RedisIntegration(),
    ],
    environment=env("ENVIRONMENT_NAME"),
    release="{}@{}".format(env("IMAGE", default=""), env("REVISION"))
    .replace(".", "-")
    .replace("/", "_"),
    send_default_pii=True,
)
ignore_logger("graphql.execution.utils")

GRAPHENE["MIDDLEWARE"].append("whoweb.core.middleware.SentryMiddleware")

# djstripe
# ------------------------------------------------------------------------------
STRIPE_LIVE_PUBLIC_KEY = env("STRIPE_LIVE_PUBLIC_KEY", default=None)
STRIPE_LIVE_SECRET_KEY = env("STRIPE_LIVE_SECRET_KEY", default=None)
STRIPE_TEST_PUBLIC_KEY = env("STRIPE_TEST_PUBLIC_KEY", default=None)
STRIPE_TEST_SECRET_KEY = env("STRIPE_TEST_SECRET_KEY", default=None)
STRIPE_LIVE_MODE = env.bool("STRIPE_LIVE_MODE", default=True)
DJSTRIPE_WEBHOOK_SECRET = env("DJSTRIPE_WEBHOOK_SECRET", default=None)
DJSTRIPE_WEBHOOK_VALIDATION = env(
    "DJSTRIPE_WEBHOOK_VALIDATION", default="verify_signature"
)  # can also be `retrieve_event`

# Your stuff...
# ------------------------------------------------------------------------------

DATAVALIDATION_KEY = env("DATAVALIDATION_KEY")
COLD_EMAIL_KEY = env("COLD_EMAIL_KEY")
COLD_ROUTER_API_KEY = env("COLD_ROUTER_API_KEY")
COLD_EMAIL_WHOIS = env("COLD_EMAIL_WHOIS")
COLD_EMAIL_PROFILEID = env("COLD_EMAIL_PROFILEID")
COLD_EMAIL_SUPRESSIONLIST = env("COLD_EMAIL_SUPRESSIONLIST")
