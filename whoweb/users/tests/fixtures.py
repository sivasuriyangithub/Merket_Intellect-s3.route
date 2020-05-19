import pytest
from django.conf import settings

from whoweb.users.models import Seat
from whoweb.users.tests.factories import UserFactory, SeatFactory


@pytest.fixture
def user() -> settings.AUTH_USER_MODEL:
    return UserFactory()


@pytest.fixture
def seat() -> Seat:
    return SeatFactory()


@pytest.fixture
def su() -> settings.AUTH_USER_MODEL:
    return UserFactory(is_superuser=True, is_staff=True)
