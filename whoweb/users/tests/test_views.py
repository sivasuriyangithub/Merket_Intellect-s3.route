from unittest.mock import patch

import bson
import pytest
from django.shortcuts import get_object_or_404

from users.tests.factories import UserFactory
from whoweb.users.models import User

pytestmark = pytest.mark.django_db


def test_impersonate_user(su_client):
    user = UserFactory()
    resp = su_client.post(
        "/ww/accounts/iadmin/", {"xperweb_id": user.username}, format="json",
    )
    assert resp.status_code == 200
    assert "token" in resp.json()
