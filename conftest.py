import pytest
from django.core.handlers.wsgi import WSGIRequest
from django.test import RequestFactory
from graphene.test import Client
from rest_framework.test import APIClient, APIRequestFactory

from config.schema import schema

pytest_plugins = [
    "whoweb.users.tests.fixtures",
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
def request_factory() -> RequestFactory:
    return RequestFactory()


@pytest.fixture
def api_factory() -> APIRequestFactory:
    return APIRequestFactory()


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def gqlclient() -> Client:
    return Client(schema)


@pytest.fixture
def context(request_factory) -> WSGIRequest:
    return request_factory.get("/ww/graphql")


@pytest.fixture
def su_client(su, api_client) -> APIClient:
    api_client.force_authenticate(user=su)
    return api_client


@pytest.fixture(scope="module")
def vcr_config():
    return {
        # Replace the Authorization request header with "DUMMY" in cassettes
        "filter_headers": [("authorization", "DUMMY")],
    }
