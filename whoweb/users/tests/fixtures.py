import pytest
from django.conf import settings

from whoweb.users.tests.factories import UserFactory


@pytest.fixture
def user() -> settings.AUTH_USER_MODEL:
    return UserFactory()


@pytest.fixture
def su() -> settings.AUTH_USER_MODEL:
    return UserFactory(is_superuser=True, is_staff=True)
