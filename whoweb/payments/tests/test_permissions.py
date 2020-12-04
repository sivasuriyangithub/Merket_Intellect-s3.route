import pytest

from whoweb.payments.tests.factories import (
    BillingAccountOwnerFactory,
    BillingAccountMemberFactory,
)
from whoweb.users.models import Group, User
from whoweb.users.tests.factories import NetworkFactory, GroupFactory, SeatFactory

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


def test_grant_default_permission():
    owner = BillingAccountOwnerFactory(organization_user__seat_credits=0)
    acct = owner.organization

    assert owner.organization_user.user.groups.exists() is False
    acct.grant_plan_permissions_for_members()
    assert owner.organization_user.user.groups.first() == acct.plan.permission_group


def test_revoke_default_permission():
    owner = BillingAccountOwnerFactory(organization_user__seat_credits=0)
    acct = owner.organization

    acct.grant_plan_permissions_for_members()
    assert owner.organization_user.user.groups.first() == acct.plan.permission_group
    acct.revoke_plan_permissions_for_members()
    assert owner.organization_user.user.groups.exists() is False


def test_revoke_default_permission_when_double_granted():
    permission_group = GroupFactory()
    owner = BillingAccountOwnerFactory(
        organization_user__seat_credits=0,
        organization_user__organization__plan__permission_group=permission_group,
    )
    acct = owner.organization

    second_seat = SeatFactory(user=owner.organization_user.user)
    second_owner = BillingAccountOwnerFactory(
        organization_user__seat=second_seat,
        organization_user__seat_credits=0,
        organization_user__organization__plan__permission_group=permission_group,
    )
    second_acct = second_owner.organization

    assert acct.plan.permission_group == permission_group
    assert second_acct.plan.permission_group == permission_group

    user = owner.organization_user.user
    assert user == second_owner.organization_user.user

    acct.grant_plan_permissions_for_members()
    second_acct.grant_plan_permissions_for_members()

    assert user.groups.first() == permission_group
    acct.revoke_plan_permissions_for_members()
    assert user.groups.first() == permission_group
    second_acct.revoke_plan_permissions_for_members()
    assert owner.organization_user.user.groups.exists() is False
