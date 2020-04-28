from unittest.mock import patch

import bson
import pytest

from whoweb.payments.tests.factories import BillingAccountMemberFactory

pytestmark = pytest.mark.django_db


@patch("whoweb.payments.serializers.su_passthrough.sync_subscriber")
def test_create_billing_seat_for_passthrough(sync_mock, su_client):
    resp = su_client.post(
        "/ww/api/admin/seats/",
        {
            "display_name": "test user",
            "first_name": "A",
            "last_name": "B",
            "xperweb_id": str(bson.ObjectId()),
            "customer_id": "cus_test001",
            "group_name": None,
            "group_id": "public",
            "email": "test@whoknows.com",
            "seat_credits": 100000,
            "credits_per_enrich": 100,
            "credits_per_work_email": 200,
            "credits_per_personal_email": 300,
            "credits_per_phone": 400,
        },
        format="json",
    )
    assert resp.status_code == 201
    assert resp.json()["url"].startswith("http://testserver/ww/api/seats/")
    assert sync_mock.call_count == 1
    network_url = resp.json()["network"]
    network = su_client.get(network_url, format="json",)
    assert network.json()["slug"] == "public"


def test_passthrough_updates_credits(su_client):
    seat = BillingAccountMemberFactory(seat_credits=0).seat
    original = su_client.get(f"/ww/api/admin/seats/{seat.public_id}/", format="json",)
    # assert original.json()["seat_credits"] == 0

    resp = su_client.patch(
        f"/ww/api/admin/seats/{seat.public_id}/",
        {"seat_credits": 100001,},
        format="json",
    )
    assert resp.status_code == 200
    seat.billing.refresh_from_db(fields=("seat_credits",))
    assert seat.billing.seat_credits == 100001


def test_set_member_credits(su_client):
    seat = BillingAccountMemberFactory(seat_credits=0)
    org = seat.organization
    org.credit_pool = 20000
    org.save()
    assert seat.credits == 0

    resp = su_client.post(
        f"/ww/api/billing_accounts/{org.public_id}/credits/",
        {"credits": 14000, "billing_seat": seat.public_id,},
        format="json",
    )
    print(resp.content)
    assert resp.status_code == 200
    assert resp.json()["pool_credits"] == False
    assert resp.json()["credits"] == 14000


def test_set_member_should_pool(su_client):
    seat = BillingAccountMemberFactory(seat_credits=10000)
    assert seat.credits == 10000
    assert seat.pool_credits == False

    resp = su_client.post(
        f"/ww/api/billing_accounts/{seat.organization.public_id}/credits/",
        {"pool": True, "billing_seat": seat.public_id,},
        format="json",
    )
    print(resp.content)
    assert resp.status_code == 200
    assert resp.json()["pool_credits"] == True
    assert resp.json()["credits"] == 10000
