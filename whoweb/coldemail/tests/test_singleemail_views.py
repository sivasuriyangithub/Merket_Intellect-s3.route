from datetime import datetime, timedelta

import pytest
from django.utils import timezone

from whoweb.coldemail.tests.factories import (
    CampaignMessageFactory,
    SingleColdEmailFactory,
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


def test_create_single_email(su_client):
    seat = BillingAccountMemberFactory()
    msg = CampaignMessageFactory(billing_seat=seat)
    resp = su_client.post(
        "/ww/api/single_emails/",
        {
            "email": "test@email.com",
            "message": msg.public_id,
            "test": True,
            "tags": ["apple"],
            "from_name": "Joe Engels",
            "use_credits_method": "2",
            "send_date": datetime.utcnow(),
            "billing_seat": seat.public_id,
        },
        format="json",
    )
    assert resp.status_code == 201, resp.content
    assert resp.json()["url"].startswith("http://testserver/ww/api/single_emails/")
    assert resp.json()["email"] == "test@email.com"

    listed = su_client.get("/ww/api/single_emails/", format="json",)
    assert len(listed.json()["results"]) == 1


def test_update_single_email(su_client):
    seat = BillingAccountMemberFactory()
    msg = CampaignMessageFactory(billing_seat=seat)
    resp = su_client.post(
        "/ww/api/single_emails/",
        {
            "email": "test@email.com",
            "message": msg.public_id,
            "test": True,
            "tags": ["apple"],
            "from_name": "Joe Engels",
            "use_credits_method": "2",
            "send_date": "2020-02-11T04:03:22",
            "billing_seat": seat.public_id,
        },
        format="json",
    )
    assert resp.status_code == 201, resp.content
    assert resp.json()["email"] == "test@email.com"

    url = resp.json()["url"]
    update = su_client.patch(url, {"send_date": "2021-02-11T04:00:00"}, format="json",)
    assert update.json()["send_date"] == "2021-02-11T04:00:00-08:00"
    assert update.json()["email"] == "test@email.com"


def test_delete_campaignmessage(su_client):
    email = SingleColdEmailFactory()
    delete = su_client.delete(
        f"/ww/api/single_emails/{email.public_id}/", format="json",
    )
    assert delete.status_code == 204, delete.content

    listed = su_client.get("/ww/api/single_emails/", format="json",)
    assert len(listed.json()["results"]) == 0
