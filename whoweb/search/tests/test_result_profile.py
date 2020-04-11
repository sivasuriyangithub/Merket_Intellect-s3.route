from unittest.mock import patch

import pytest

from whoweb.payments.tests.factories import BillingAccountMemberFactory
from whoweb.search.models import ResultProfile, DerivedContact
from .fixtures import pending, done


def test_load_underived_profile():
    result_profile = ResultProfile(**pending[0])
    assert result_profile.email is None
    assert "Tirlea" == result_profile.last_name


def test_load_derivation():
    derivation = DerivedContact(**done[0])
    assert "patrick@beast.vc" == derivation.email


def test_load_derived_profile():
    result_profile = ResultProfile(**done[0])
    assert "patrick@beast.vc" == result_profile.email
    assert "Strong" == result_profile.last_name


def test_load_unload_underived_profile():
    result_profile = ResultProfile(**pending[0])
    once = result_profile.dict()
    loaded = ResultProfile(**once)
    assert result_profile.last_name, loaded.last_name
    assert once == loaded.dict()


def test_load_unload_derived_profile():
    result_profile = ResultProfile(**done[0])

    once = result_profile.dict()
    loaded = ResultProfile(**once)

    assert result_profile.last_name == loaded.last_name
    assert once == loaded.dict()


@pytest.mark.django_db
@patch("whoweb.core.router.Router.derive_email")
def test_derive_profile(derive_mock, su_client):
    seat = BillingAccountMemberFactory(seat_credits=10000).seat
    derive_mock.return_value = done[0]
    resp = su_client.post(
        "/ww/api/profiles/derive/",
        {
            "first_name": done[0]["first_name"],
            "last_name": done[0]["last_name"],
            "company": done[0]["company"],
            "id": done[0]["profile_id"],
            "seat": seat.public_id,
        },
        format="json",
    )
    print(resp.content)
    assert resp.status_code == 201
    assert resp.json()["email"] == "patrick@beast.vc"
    assert resp.json()["credits_used"] == 100


@pytest.mark.django_db
@patch("whoweb.core.router.Router.derive_email")
def test_derive_profile_cached_charges(derive_mock, su_client):
    seat = BillingAccountMemberFactory(seat_credits=10000).seat
    derive_mock.return_value = done[0]
    payload = {
        "first_name": done[0]["first_name"],
        "last_name": done[0]["last_name"],
        "company": done[0]["company"],
        "id": done[0]["profile_id"],
        "seat": seat.public_id,
    }
    resp = su_client.post("/ww/api/profiles/derive/", payload, format="json",)
    assert resp.status_code == 201
    assert resp.json()["credits_used"] == 100

    resp2 = su_client.post("/ww/api/profiles/derive/", payload, format="json",)
    assert resp2.status_code == 201
    assert resp2.json()["credits_used"] == 0
