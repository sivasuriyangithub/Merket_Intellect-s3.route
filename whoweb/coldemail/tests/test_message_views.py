import pytest

from whoweb.coldemail.tests.factories import (
    CampaignMessageFactory,
    CampaignMessageTemplateFactory,
)
from whoweb.payments.tests.factories import BillingAccountMemberFactory

pytestmark = pytest.mark.django_db

TEST_QUERY = {
    "user_id": None,
    "filters": {"limit": 10, "skip": 0, "required": [], "desired": [], "profiles": [],},
    "defer": [],
    "with_invites": False,
    "contact_filters": [],
    "export": {"webhooks": [], "title": "", "metadata": {}, "format": "nested",},
}


def test_create_campaignmessage(su_client):
    seat = BillingAccountMemberFactory()
    resp = su_client.post(
        "/ww/api/campaign/messages/",
        {
            "title": "test",
            "subject": "Click here",
            "html_content": "<h1>Yo</h1>",
            "tags": ["apple"],
            "sender_id": "1",
            "suppression_group_id": "2",
            "plain_content": "Yo!",
            "editor": "client",
            "billing_seat": seat.public_id,
        },
        format="json",
    )
    print(resp.content)
    assert resp.status_code == 201
    assert resp.json()["url"].startswith("http://testserver/ww/api/campaign/messages/")
    assert resp.json()["title"] == "test"

    listed = su_client.get("/ww/api/campaign/messages/", format="json",)
    assert len(listed.json()["results"]) == 1


def test_update_campaignmessage(su_client):
    seat = BillingAccountMemberFactory()
    resp = su_client.post(
        "/ww/api/campaign/messages/",
        {
            "title": "test",
            "subject": "Click here",
            "html_content": "<h1>Yo</h1>",
            "tags": ["apple"],
            "sender_id": "1",
            "suppression_group_id": "2",
            "plain_content": "Yo!",
            "editor": "client",
            "billing_seat": seat.public_id,
        },
        format="json",
    )
    url = resp.json()["url"]
    assert resp.status_code == 201
    assert resp.json()["title"] == "test"

    update = su_client.patch(url, {"title": "new title"}, format="json",)
    assert update.json()["title"] == "new title"
    assert update.json()["editor"] == resp.json()["editor"] == "client"


def test_delete_campaignmessage(su_client):
    msg = CampaignMessageFactory()
    delete = su_client.delete(
        f"/ww/api/campaign/messages/{msg.public_id}/", format="json",
    )
    print(msg.public_id)
    assert delete.status_code == 204

    listed = su_client.get("/ww/api/campaign/messages/", format="json",)
    assert len(listed.json()["results"]) == 0


def test_create_campaignmessage_template(su_client):
    seat = BillingAccountMemberFactory()
    resp = su_client.post(
        "/ww/api/campaign/message_templates/",
        {
            "title": "test",
            "subject": "Click here",
            "html_content": "<h1>Yo</h1>",
            "tags": ["apple"],
            "sender_id": "1",
            "suppression_group_id": "2",
            "plain_content": "Yo!",
            "editor": "client",
            "billing_seat": seat.public_id,
        },
        format="json",
    )
    print(resp.content)
    assert resp.status_code == 201
    assert resp.json()["url"].startswith(
        "http://testserver/ww/api/campaign/message_templates/"
    )
    assert resp.json()["title"] == "test"

    listed = su_client.get("/ww/api/campaign/message_templates/", format="json",)
    assert len(listed.json()["results"]) == 1


def test_update_campaignmessage_template(su_client):
    seat = BillingAccountMemberFactory()
    resp = su_client.post(
        "/ww/api/campaign/message_templates/",
        {
            "title": "test",
            "subject": "Click here",
            "html_content": "<h1>Yo</h1>",
            "tags": ["apple"],
            "sender_id": "1",
            "suppression_group_id": "2",
            "plain_content": "Yo!",
            "editor": "client",
            "billing_seat": seat.public_id,
        },
        format="json",
    )
    url = resp.json()["url"]
    assert resp.status_code == 201
    assert resp.json()["title"] == "test"

    update = su_client.patch(url, {"title": "new title"}, format="json",)
    assert update.json()["title"] == "new title"
    assert update.json()["editor"] == resp.json()["editor"] == "client"


def test_delete_campaignmessage_template(su_client):
    msg = CampaignMessageTemplateFactory()
    delete = su_client.delete(
        f"/ww/api/campaign/message_templates/{msg.public_id}/", format="json",
    )
    assert delete.status_code == 204

    listed = su_client.get("/ww/api/campaign/message_templates/", format="json",)
    assert len(listed.json()["results"]) == 0
