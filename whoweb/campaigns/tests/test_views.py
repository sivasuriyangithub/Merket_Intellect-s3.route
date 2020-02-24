from unittest.mock import patch

import pytest

from whoweb.coldemail.tests.factories import CampaignMessageFactory
from whoweb.payments.tests.factories import BillingAccountMemberFactory

pytestmark = pytest.mark.django_db


def test_create_simple_campaign(su_client, query_contact_invites):
    seat = BillingAccountMemberFactory().seat
    msg0 = CampaignMessageFactory(seat=seat)
    resp = su_client.post(
        "/ww/api/campaign/simple/",
        {
            "query": query_contact_invites,
            "budget": 500,
            "seat": seat.public_id,
            "tags": ["apple", "banana"],
            "sending_rules": [
                {
                    "message": msg0.public_id,
                    "index": 0,
                    "trigger": 0,
                    "send_datetime": "2017-09-29 09:15:00Z",
                }
            ],
        },
        format="json",
    )
    print(resp.content)
    assert resp.status_code == 201
    assert resp.json()["url"].startswith("http://testserver/ww/api/campaign/simple/")
    assert resp.json()["budget"] == 500

    listed = su_client.get("/ww/api/campaign/simple/", format="json",)
    assert len(listed.json()["results"]) == 1


@patch("whoweb.campaigns.models.SimpleDripCampaignRunner.publish")
def test_publish_simplecampaign(publish_mock, su_client, query_contact_invites):
    seat = BillingAccountMemberFactory().seat
    resp = su_client.post(
        "/ww/api/campaign/simple/",
        {
            "query": query_contact_invites,
            "budget": 500,
            "sending_rules": [],
            "seat": seat.public_id,
        },
        format="json",
    )
    url = resp.json()["url"]
    su_client.post(
        url + "publish/", format="json",
    )
    assert publish_mock.call_count == 1


def test_create_interval_campaign(su_client, query_contact_invites):
    seat = BillingAccountMemberFactory().seat
    msg0 = CampaignMessageFactory(seat=seat)
    msg1 = CampaignMessageFactory(seat=seat)
    resp = su_client.post(
        "/ww/api/campaign/interval/",
        {
            "query": query_contact_invites,
            "budget": 500,
            "tags": ["apple", "banana"],
            "sending_rules": [
                {
                    "message": msg0.public_id,
                    "index": 0,
                    "trigger": 0,
                    "send_datetime": "2017-09-29 09:15:00Z",
                },
                {
                    "message": msg1.public_id,
                    "index": 1,
                    "trigger": 1,
                    "send_delta": 186000,
                    "include_previous": True,
                },
            ],
            "seat": seat.public_id,
        },
        format="json",
    )
    print(resp.content)
    assert resp.status_code == 201
    assert resp.json()["url"].startswith("http://testserver/ww/api/campaign/interval/")
    assert resp.json()["budget"] == 500

    listed = su_client.get("/ww/api/campaign/interval/", format="json",)
    assert len(listed.json()["results"]) == 1


@patch("whoweb.campaigns.models.IntervalCampaignRunner.publish")
def test_publish_intervalcampaign(publish_mock, su_client, query_contact_invites):
    seat = BillingAccountMemberFactory().seat
    resp = su_client.post(
        "/ww/api/campaign/interval/",
        {
            "query": query_contact_invites,
            "budget": 500,
            "sending_rules": [],
            "seat": seat.public_id,
        },
        format="json",
    )
    url = resp.json()["url"]
    su_client.post(
        url + "publish/", format="json",
    )
    assert publish_mock.call_count == 1
