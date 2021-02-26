import pytest

from whoweb.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def test_impersonate_user(su_client):
    user = UserFactory()
    resp = su_client.post(
        "/ww/accounts/iadmin/", {"xperweb_id": user.profile.xperweb_id}, format="json",
    )
    assert resp.status_code == 200
    assert "token" in resp.json()
