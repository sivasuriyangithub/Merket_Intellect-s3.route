import pytest

from whoweb.coldemail.tests.factories import CampaignMessageFactory
from whoweb.payments.tests.factories import BillingAccountMemberFactory

pytestmark = pytest.mark.django_db


def test_create_campaignlist(su_client, query_contact_invites):
    seat = BillingAccountMemberFactory()
    resp = su_client.post(
        "/ww/api/campaign/lists/",
        {
            "query": query_contact_invites,
            "name": "list name",
            "origin": "USER",
            "tags": [],
            "billing_seat": seat.public_id,
        },
        format="json",
    )
    assert resp.status_code == 201, resp.content
    assert resp.json()["url"].startswith("http://testserver/ww/api/campaign/lists/")
    assert resp.json()["name"] == "list name"

    listed = su_client.get("/ww/api/campaign/lists/", format="json",)
    assert len(listed.json()["results"]) == 1


def test_update_campaignlist(su_client, query_contact_invites):
    seat = BillingAccountMemberFactory()
    resp = su_client.post(
        "/ww/api/campaign/lists/",
        {
            "query": query_contact_invites,
            "name": "list name",
            "origin": "USER",
            "tags": [],
            "billing_seat": seat.public_id,
        },
        format="json",
    )
    url = resp.json()["url"]
    assert resp.status_code == 201, resp.content
    assert resp.json()["name"] == "list name"

    update = su_client.patch(url, {"name": "new name"}, format="json",)
    assert update.json()["name"] == "new name"


def test_delete_campaignlist(su_client, query_contact_invites):
    seat = BillingAccountMemberFactory()
    resp = su_client.post(
        "/ww/api/campaign/lists/",
        {
            "query": query_contact_invites,
            "name": "list name",
            "origin": "USER",
            "tags": [],
            "billing_seat": seat.public_id,
        },
        format="json",
    )
    url = resp.json()["url"]
    delete = su_client.delete(url, format="json",)
    assert delete.status_code == 204, resp.content

    listed = su_client.get("/ww/api/campaign/lists/", format="json",)
    assert len(listed.json()["results"]) == 0
