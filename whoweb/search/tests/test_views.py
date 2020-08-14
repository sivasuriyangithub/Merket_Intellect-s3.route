from collections import OrderedDict
from unittest.mock import patch

import pytest
from graphql_relay import to_global_id

from whoweb.payments.tests.factories import BillingAccountMemberFactory
from whoweb.search.tests.factories import DerivationCacheRecordFactory

pytestmark = pytest.mark.django_db


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
    assert resp.json()["profile"]["email"] == "patrick@beast.vc"
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


from string import Template


@pytest.mark.django_db
def test_derive_profile_shows_in_feed(gqlclient, context, user):
    seat = BillingAccountMemberFactory(seat_credits=10000, user=user)
    _included = DerivationCacheRecordFactory(billing_seat=seat, profile_id="wp:1")
    _excluded = DerivationCacheRecordFactory(billing_seat=BillingAccountMemberFactory())
    gql = Template(
        """
    query {
      derivations(billingSeat:"$billing", profileId_In:"wp:1,wp:2"){
        edges{
          node{
            profileId
          }
        }
      }
    }
    """
    ).substitute(billing=to_global_id("BillingAccountMemberNode", seat.public_id))

    context.user = user
    executed = gqlclient.execute(gql, context=context)
    assert executed["data"]["derivations"] == OrderedDict(
        [("edges", [OrderedDict([("node", OrderedDict([("profileId", "wp:1")]))])],)]
    )


@patch("whoweb.core.router.Router.unified_search")
@patch("whoweb.core.router.Router.derive_email")
def test_derive_profile_no_id(
    derive_mock, unified_search_mock, su_client, raw_derived, search_results
):
    seat = BillingAccountMemberFactory(seat_credits=10000)
    unified_search_mock.return_value = {"results": search_results}
    derive_mock.return_value = raw_derived[0]
    resp = su_client.post(
        "/ww/api/profiles/derive/",
        {
            "first_name": raw_derived[0]["first_name"],
            "last_name": raw_derived[0]["last_name"],
            "company": raw_derived[0]["company"],
            "billing_seat": seat.public_id,
        },
        format="json",
    )
    assert resp.status_code == 201
    assert resp.json()["profile"]["email"] == "patrick@beast.vc"
    assert resp.json()["credits_used"] == 100


@patch("whoweb.core.router.Router.profile_lookup")
@patch("whoweb.core.router.Router.derive_email")
def test_derive_profile_only_id(
    derive_mock, profile_search_mock, su_client, raw_derived, search_results
):
    seat = BillingAccountMemberFactory(seat_credits=10000)
    profile_search_mock.return_value = {"results": search_results}
    derive_mock.return_value = raw_derived[0]
    resp = su_client.post(
        "/ww/api/profiles/derive/",
        {"id": raw_derived[0]["profile_id"], "billing_seat": seat.public_id,},
        format="json",
    )
    assert resp.status_code == 201
    assert resp.json()["profile"]["email"] == "patrick@beast.vc"
    assert resp.json()["credits_used"] == 100


@patch("whoweb.core.router.Router.unified_search")
@patch("whoweb.core.router.Router.profile_lookup")
def test_enrich_profile(
    profile_search_mock, unified_search_mock, su_client, search_results
):
    seat = BillingAccountMemberFactory(seat_credits=10000)
    unified_search_mock.return_value = {"results": search_results}
    profile_search_mock.return_value = {"results": search_results}
    resp = su_client.post(
        "/ww/api/profiles/enrich/",
        {
            "profile_id": search_results[0]["profile_id"],
            "billing_seat": seat.public_id,
        },
        format="json",
    )
    assert resp.status_code == 201
    assert "industry" in resp.json()["profile"]
    assert resp.json()["credits_used"] == 25
