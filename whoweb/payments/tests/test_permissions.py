import pytest

from whoweb.users.models import Group, User
from whoweb.users.tests.factories import NetworkFactory

pytestmark = pytest.mark.django_db


def test_org_owner_can_create_billing_account(user, api_client):
    network: Group = NetworkFactory()
    seat, created = network.get_or_add_user(user)
    api_client.force_authenticate(user)
    resp = api_client.post(
        f"/ww/api/billing_accounts/",
        {
            "name": f"{user.email} Primary ({user.username})",
            "network": network.public_id,
        },
        format="json",
    )
    assert resp.status_code == 201
    user = User.objects.get(pk=user.pk)
    assert user.has_perms(
        ["payments.add_billingaccountmember", "payments.view_billingaccountmember"]
    )
    billing_account = resp.json()["url"]
    create_member = api_client.post(
        f"/ww/api/billing_seats/",
        {"seat": seat.public_id, "billing_account": billing_account,},
        format="json",
    )
    assert create_member.status_code == 201
    seat.refresh_from_db()
    assert seat.billing
