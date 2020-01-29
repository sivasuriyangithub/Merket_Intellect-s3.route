import pytest
from django.conf import settings
from django.test import RequestFactory

from whoweb.users.tests.factories import UserFactory

pytest_plugins = [
    "whoweb.search.tests.fixtures",
    "whoweb.coldemail.tests.fixtures",
]


@pytest.fixture(scope="session")
def celery_enable_logging():
    # type: () -> bool
    """You can override this fixture to enable logging."""
    return True


@pytest.fixture(scope="session")
def celery_worker_pool():
    # type: () -> Union[str, Any]
    """You can override this fixture to set the worker pool.

    The "solo" pool is used by default, but you can set this to
    return e.g. "prefork".
    """
    return "solo"


#
# @pytest.fixture(scope="session")
# def celery_config():
#     # return {"broker_url": "memory://", "result_backend": "redis://"}
#     return {"broker_url": "memory://", "result_backend": settings.CELERY_RESULT_BACKEND}


@pytest.fixture(autouse=True)
def media_storage(settings, tmpdir):
    settings.MEDIA_ROOT = tmpdir.strpath


@pytest.fixture
def user() -> settings.AUTH_USER_MODEL:
    return UserFactory()


@pytest.fixture
def request_factory() -> RequestFactory:
    return RequestFactory()
