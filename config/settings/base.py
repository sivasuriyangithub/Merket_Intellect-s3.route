"""
Base settings to build other settings files upon.
"""
from datetime import timedelta

import environ

ROOT_DIR = environ.Path(__file__) - 3  # (whoweb/config/settings/base.py - 3 = whoweb/)
APPS_DIR = ROOT_DIR.path("whoweb")

env = environ.Env()

READ_DOT_ENV_FILE = env.bool("DJANGO_READ_DOT_ENV_FILE", default=False)
if READ_DOT_ENV_FILE:
    # OS environment variables take precedence over variables from .env
    env.read_env(str(ROOT_DIR.path(".env")))

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = env.bool("DJANGO_DEBUG", False)
# Local time zone. Choices are
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# though not all of them may be available with every OS.
# In Windows, this must be set to your system time zone.
TIME_ZONE = "America/Los_Angeles"
# https://docs.djangoproject.com/en/dev/ref/settings/#language-code
LANGUAGE_CODE = "en-us"
# https://docs.djangoproject.com/en/dev/ref/settings/#site-id
SITE_ID = 1
# https://docs.djangoproject.com/en/dev/ref/settings/#use-i18n
USE_I18N = True
# https://docs.djangoproject.com/en/dev/ref/settings/#use-l10n
USE_L10N = True
# https://docs.djangoproject.com/en/dev/ref/settings/#use-tz
USE_TZ = True
DATETIME_FORMAT = "N j, Y, P T"
# https://docs.djangoproject.com/en/dev/ref/settings/#locale-paths
LOCALE_PATHS = [ROOT_DIR.path("locale")]

ENVIRONMENT_NAME = env("ENVIRONMENT_NAME", default="")

# DATABASES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#databases
DATABASES = {"default": env.db("DATABASE_URL")}
DATABASES["default"]["ATOMIC_REQUESTS"] = True
DATABASES["default"]["OPTIONS"] = {"connect_timeout": 3}

# https://docs.djangoproject.com/en/dev/ref/settings/#disable-server-side-cursors
DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = True  # using pgbouncer


# URLS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#root-urlconf
ROOT_URLCONF = "config.urls"
# https://docs.djangoproject.com/en/dev/ref/settings/#wsgi-application
WSGI_APPLICATION = "config.wsgi.application"

# APPS
# ------------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    # "django.contrib.humanize", # Handy template tags
    "admin_actions",
    "django.contrib.admin",
]
THIRD_PARTY_APPS = [
    "inline_actions",
    "crispy_forms",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "rest_framework",
    "graphene_django",
    "djstripe",
    "django_celery_beat",
    "django_celery_results",
    "django_filters",
    "guardian",
    "organizations",
    "prettyjson",
    "polymorphic",
    "tagulous",
]

LOCAL_APPS = [
    "whoweb.core.apps.CoreConfig",
    "whoweb.users.apps.UsersConfig",
    "whoweb.coldemail.apps.ColdemailConfig",
    "whoweb.campaigns.apps.CampaignsConfig",
    "whoweb.search.apps.SearchConfig",
    "whoweb.accounting.apps.AccountingConfig",
    "whoweb.payments.apps.PaymentsConfig",
]
# https://docs.djangoproject.com/en/dev/ref/settings/#installed-apps
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# MIGRATIONS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#migration-modules
MIGRATION_MODULES = {"sites": "whoweb.contrib.sites.migrations"}

# AUTHENTICATION
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#authentication-backends
AUTHENTICATION_BACKENDS = [
    "graphql_jwt.backends.JSONWebTokenBackend",
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
    "guardian.backends.ObjectPermissionBackend",
]
# https://docs.djangoproject.com/en/dev/ref/settings/#auth-user-model
AUTH_USER_MODEL = "users.User"
# https://django-guardian.readthedocs.io/en/stable/userguide/custom-user-model.html
GUARDIAN_MONKEY_PATCH = False
# https://docs.djangoproject.com/en/dev/ref/settings/#login-redirect-url
LOGIN_REDIRECT_URL = "users:redirect"
# https://docs.djangoproject.com/en/dev/ref/settings/#login-url
LOGIN_URL = "account_login"

# PASSWORDS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#password-hashers
PASSWORD_HASHERS = [
    # https://docs.djangoproject.com/en/dev/topics/auth/passwords/#using-argon2-with-django
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]
# https://docs.djangoproject.com/en/dev/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# MIDDLEWARE
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#middleware
MIDDLEWARE = [
    "whoweb.core.middleware.HealthCheckMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# STATIC
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#static-root
STATIC_ROOT = str(ROOT_DIR("staticfiles"))
# https://docs.djangoproject.com/en/dev/ref/settings/#static-url
STATIC_URL = "/ww/static/"
# https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#std:setting-STATICFILES_DIRS
STATICFILES_DIRS = [str(APPS_DIR.path("static"))]
# https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#staticfiles-finders
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

# MEDIA
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#media-root
MEDIA_ROOT = str(APPS_DIR("media"))
# https://docs.djangoproject.com/en/dev/ref/settings/#media-url
MEDIA_URL = "/media/"

# TEMPLATES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#templates
TEMPLATES = [
    {
        # https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-TEMPLATES-BACKEND
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # https://docs.djangoproject.com/en/dev/ref/settings/#template-dirs
        "DIRS": [str(APPS_DIR.path("templates"))],
        "OPTIONS": {
            # https://docs.djangoproject.com/en/dev/ref/settings/#template-loaders
            # https://docs.djangoproject.com/en/dev/ref/templates/api/#loader-types
            "loaders": [
                "django.template.loaders.filesystem.Loader",
                "django.template.loaders.app_directories.Loader",
            ],
            # https://docs.djangoproject.com/en/dev/ref/settings/#template-context-processors
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

# http://django-crispy-forms.readthedocs.io/en/latest/install.html#template-packs
CRISPY_TEMPLATE_PACK = "bootstrap4"

# FIXTURES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#fixture-dirs
FIXTURE_DIRS = (str(APPS_DIR.path("fixtures")),)

# SECURITY
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#session-cookie-httponly
SESSION_COOKIE_HTTPONLY = True
# https://docs.djangoproject.com/en/dev/ref/settings/#csrf-cookie-httponly
CSRF_COOKIE_HTTPONLY = True
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-browser-xss-filter
SECURE_BROWSER_XSS_FILTER = True
# https://docs.djangoproject.com/en/dev/ref/settings/#x-frame-options
X_FRAME_OPTIONS = "DENY"

# EMAIL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = env(
    "DJANGO_EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend"
)
# https://docs.djangoproject.com/en/2.2/ref/settings/#email-timeout
EMAIL_TIMEOUT = 5

# ADMIN
# ------------------------------------------------------------------------------
# Django Admin URL.
ADMIN_URL = "admin/"
# https://docs.djangoproject.com/en/dev/ref/settings/#admins
ADMINS = [("""WhoKnows, Inc.""", "dev@whoknows.com")]
# https://docs.djangoproject.com/en/dev/ref/settings/#managers
MANAGERS = ADMINS

# LOGGING
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#logging
# See https://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(levelname)s %(asctime)s %(module)s "
            "%(process)d %(thread)d %(message)s"
        }
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        }
    },
    "root": {"level": env("DJANGO_LOG_LEVEL", default="INFO"), "handlers": ["console"]},
}

# Celery
# ------------------------------------------------------------------------------
if USE_TZ:
    # http://docs.celeryproject.org/en/latest/userguide/configuration.html#std:setting-timezone
    CELERY_TIMEZONE = TIME_ZONE
# http://docs.celeryproject.org/en/latest/userguide/configuration.html#std:setting-broker_url
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="")
CELERY_BROKER_VHOST = env("CELERY_BROKER_VHOST", default="")
if CELERY_BROKER_VHOST:
    CELERY_BROKER_URL = f"{CELERY_BROKER_URL}/{CELERY_BROKER_VHOST}"
# http://docs.celeryproject.org/en/latest/userguide/configuration.html#std:setting-result_backend
CELERY_RESULT_BACKEND = env("REDIS_URL", default="django-db")
# https://docs.celeryproject.org/en/latest/django/first-steps-with-django.html
CELERY_CACHE_BACKEND = "default"
# http://docs.celeryproject.org/en/latest/userguide/configuration.html#std:setting-accept_content
CELERY_ACCEPT_CONTENT = ["json"]
# http://docs.celeryproject.org/en/latest/userguide/configuration.html#std:setting-task_serializer
CELERY_TASK_SERIALIZER = "json"
# http://docs.celeryproject.org/en/latest/userguide/configuration.html#std:setting-result_serializer
CELERY_RESULT_SERIALIZER = "json"
# http://docs.celeryproject.org/en/latest/userguide/configuration.html#task-ignore-result
CELERY_TASK_IGNORE_RESULT = False
CELERY_RESULT_EXTENDED = True
CELERY_RESULT_EXPIRES = timedelta(days=5)
CELERY_RESULT_CHORD_JOIN_TIMEOUT = 20.0
# http://docs.celeryproject.org/en/latest/userguide/configuration.html#task-time-limit
CELERY_TASK_TIME_LIMIT = 60 * 60
# http://docs.celeryproject.org/en/latest/userguide/configuration.html#task-soft-time-limit
CELERY_TASK_SOFT_TIME_LIMIT = None
# http://docs.celeryproject.org/en/latest/userguide/configuration.html#beat-scheduler
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
# https://docs.celeryproject.org/en/latest/userguide/routing.html#changing-the-name-of-the-default-queue
CELERY_TASK_DEFAULT_QUEUE = "whoweb"
# https://docs.celeryproject.org/en/latest/userguide/configuration.html#std:setting-task_routes
CELERY_TASK_ROUTES = {
    "whoweb.search.tasks.fetch_mx_domains": {"queue": "whoweb_low"},
    "whoweb.search.tasks.process_derivation_slow": {"queue": "whoweb_low"},
    "whoweb.search.tasks.process_derivation_fast": {"queue": "whoweb_low"},
}
# http://docs.celeryproject.org/en/latest/userguide/routing.html#routing-options-rabbitmq-priorities
CELERY_TASK_QUEUE_MAX_PRIORITY = 4  # starts at 0
CELERY_TASK_DEFAULT_PRIORITY = 2
CELERY_WORKER_PREFETCH_MULTIPLIER = 2
CELERY_REDIS_RETRY_ON_TIMEOUT = True
CELERY_WORKER_SEND_TASK_EVENTS = True
CELERY_TASK_SEND_SENT_EVENT = True
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
# https://docs.celeryproject.org/en/stable/userguide/configuration.html#task-remote-tracebacks
CELERY_TASK_REMOTE_TRACEBACKS = True
# django-allauth
# ------------------------------------------------------------------------------
ACCOUNT_ALLOW_REGISTRATION = env.bool("DJANGO_ACCOUNT_ALLOW_REGISTRATION", True)
# https://django-allauth.readthedocs.io/en/latest/configuration.html
ACCOUNT_AUTHENTICATION_METHOD = "email"
# https://django-allauth.readthedocs.io/en/latest/configuration.html
ACCOUNT_EMAIL_REQUIRED = True
# https://django-allauth.readthedocs.io/en/latest/configuration.html
ACCOUNT_UNIQUE_EMAIL = True
# https://django-allauth.readthedocs.io/en/latest/configuration.html
ACCOUNT_USERNAME_REQUIRED = False
# https://django-allauth.readthedocs.io/en/latest/advanced.html#custom-user-models
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
# https://django-allauth.readthedocs.io/en/latest/configuration.html
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
# https://django-allauth.readthedocs.io/en/latest/configuration.html
ACCOUNT_ADAPTER = "whoweb.users.adapters.AccountAdapter"
# https://django-allauth.readthedocs.io/en/latest/configuration.html
SOCIALACCOUNT_ADAPTER = "whoweb.users.adapters.SocialAccountAdapter"

# django rest framework
# ------------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.BasicAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAdminUser",  # temporary
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_SCHEMA_CLASS": "whoweb.contrib.rest_framework.schemas.VerboseAutoSchema",
    # "DEFAULT_RENDERER_CLASSES": [
    #     "rest_framework.renderers.JSONRenderer",
    #     "whoweb.contrib.rest_framework.renderers.CustomBrowsableAPIRenderer",
    # ],
    "DEFAULT_FILTER_BACKENDS": ("django_filters.rest_framework.DjangoFilterBackend",),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

SIMPLE_JWT = {
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.SlidingToken",),
    "SLIDING_TOKEN_LIFETIME": timedelta(minutes=15),
    "SLIDING_TOKEN_REFRESH_LIFETIME": timedelta(days=14),
    "USER_ID_FIELD": "email",
    "USER_ID_CLAIM": "username",
}
# graphene
# ------------------------------------------------------------------------------
# https://docs.graphene-python.org/projects/django/en/latest/installation/
GRAPHENE = {
    "SCHEMA": "config.schema.schema",
    "MIDDLEWARE": [
        "graphql_jwt.middleware.JSONWebTokenMiddleware",
        "whoweb.core.middleware.LoaderMiddleware",
    ],
}
GRAPHQL_JWT = {
    # "JWT_ALLOW_ARGUMENT": True,
    "JWT_ALLOW_ANY_CLASSES": (
        "config.schema.RereshSlidingJSONWebToken",
        "config.schema.ObtainJSONWebToken",
    ),
    "JWT_ARGUMENT_NAME": "token",
    "JWT_GET_USER_BY_NATURAL_KEY_HANDLER": "whoweb.contrib.graphql_jwt.utils.get_user_by_natural_key",
    "JWT_VERIFY_EXPIRATION": True,
    "JWT_EXPIRATION_DELTA": timedelta(minutes=15),
    "JWT_REFRESH_EXPIRATION_DELTA": timedelta(days=14),
}

# tagulous
# ------------------------------------------------------------------------------
SERIALIZATION_MODULES = {
    "xml": "tagulous.serializers.xml_serializer",
    "json": "tagulous.serializers.json",
    "python": "tagulous.serializers.python",
    "yaml": "tagulous.serializers.pyyaml",
}

# djstripe
# ------------------------------------------------------------------------------


def billing_account_request_callback(request):
    from whoweb.payments.models import BillingAccount

    return BillingAccount.objects.filter(seats__user=request.user).first()


DJSTRIPE_SUBSCRIBER_MODEL = "payments.BillingAccount"
DJSTRIPE_SUBSCRIBER_MODEL_MIGRATION_DEPENDENCY = "0007_auto_20200228_1436"
DJSTRIPE_SUBSCRIBER_MODEL_REQUEST_CALLBACK = billing_account_request_callback
DJSTRIPE_USE_NATIVE_JSONFIELD = True

# Your stuff...
# ------------------------------------------------------------------------------
ORGS_SLUGFIELD = "autoslug.fields.AutoSlugField"

# Services
namespace_prefix = env("NAMESPACE_PREFIX", default="")
PUBLIC_ORIGIN = env("PUBLIC_ORIGIN", default="https://whoknows.com")
DERIVE_SERVICE = env("DERIVE_URI", default=f"http://{namespace_prefix}derive")
ANALYTICS_SERVICE = env("XPERDATA_URI", default=f"http://{namespace_prefix}xperdata:80")
XPERWEB_URI = env("XPERWEB_URI", default=f"http://{namespace_prefix}xperweb")
