from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from whoweb.payments.tests.factories import BillingAccountMemberFactory
from whoweb.search.models import ResultProfile, DerivedContact


def test_load_underived_profile(search_results):
    result_profile = ResultProfile(**search_results[0])
    assert result_profile.email is None
    assert "Tirlea" == result_profile.last_name


def test_load_derivation(raw_derived):
    derivation = DerivedContact(**raw_derived[0])
    assert "patrick@beast.vc" == derivation.email


def test_load_derived_profile(raw_derived):
    result_profile = ResultProfile(**raw_derived[0])
    assert "patrick@beast.vc" == result_profile.email
    assert "Strong" == result_profile.last_name


def test_load_unload_underived_profile(search_results):
    for search_result in search_results:
        result_profile = ResultProfile(**search_result)
        print(result_profile)
        once = result_profile.dict()
        loaded = ResultProfile(**once)
        twice = loaded.dict()
        assert result_profile.last_name, loaded.last_name
        assert once == twice


def test_load_unload_derived_profile(raw_derived):
    result_profile = ResultProfile(**raw_derived[0])

    once = result_profile.dict()
    loaded = ResultProfile(**once)

    assert result_profile.last_name == loaded.last_name
    assert once == loaded.dict()


@pytest.mark.django_db
@patch("whoweb.core.router.Router.derive_email")
def test_derive_profile(derive_mock, su_client, raw_derived):
    seat = BillingAccountMemberFactory(seat_credits=10000)
    derive_mock.return_value = raw_derived[0]
    resp = su_client.post(
        "/ww/api/profiles/derive/",
        {
            "first_name": raw_derived[0]["first_name"],
            "last_name": raw_derived[0]["last_name"],
            "company": raw_derived[0]["company"],
            "id": raw_derived[0]["profile_id"],
            "billing_seat": seat.public_id,
        },
        format="json",
    )
    assert resp.status_code == 201
    assert resp.json()["email"] == "patrick@beast.vc"
    assert resp.json()["credits_used"] == 100


@pytest.mark.django_db
@patch("whoweb.core.router.Router.derive_email")
def test_derive_profile_cached_charges(derive_mock, su_client, raw_derived):
    seat = BillingAccountMemberFactory(seat_credits=10000)
    derive_mock.return_value = raw_derived[0]
    payload = {
        "first_name": raw_derived[0]["first_name"],
        "last_name": raw_derived[0]["last_name"],
        "company": raw_derived[0]["company"],
        "id": raw_derived[0]["profile_id"],
        "billing_seat": seat.public_id,
    }
    resp = su_client.post("/ww/api/profiles/derive/", payload, format="json",)
    assert resp.status_code == 201
    assert resp.json()["credits_used"] == 100

    resp2 = su_client.post("/ww/api/profiles/derive/", payload, format="json",)
    assert resp2.status_code == 201
    assert resp2.json()["credits_used"] == 0
