from datetime import datetime, timedelta
from unittest.mock import patch, PropertyMock

import pytest
from django.utils.timezone import now
from djstripe.enums import SubscriptionStatus
from djstripe.models import Customer

from whoweb.payments.models import BillingAccount, MultiPlanCustomer
from whoweb.payments.tests.factories import (
    BillingAccountOwnerFactory,
    WKPlanPresetFactory,
    PlanFactory,
)

pytestmark = pytest.mark.django_db


@pytest.mark.vcr()
def test_add_card_no_existing_subscription(su_client):
    billing = BillingAccountOwnerFactory(organization_user__seat_credits=0)
    billing_account: BillingAccount = billing.organization
    assert billing_account.customer is None

    resp = su_client.post(
        "/ww/api/payment_source/",
        {"stripe_token": "tok_visa", "billing_account": billing_account.public_id,},
        format="json",
    )
    assert resp.status_code == 201
    assert (
        resp.json()["billing_account"]
        == f"http://testserver/ww/api/billing_accounts/{billing_account.public_id}/"
    )

    assert billing_account.customer.can_charge() is True


@pytest.mark.vcr()
@patch("djstripe.models.Customer.subscription", new_callable=PropertyMock)
def test_add_card_has_existing_subscription_on_trial(sub_mock, su_client):
    billing = BillingAccountOwnerFactory(organization_user__seat_credits=0)
    billing_account: BillingAccount = billing.organization

    assert billing_account.customer is None

    sub_mock.return_value.status = SubscriptionStatus.trialing
    sub_mock.return_value.trial_end = now() + timedelta(1)
    resp = su_client.post(
        "/ww/api/payment_source/",
        {"stripe_token": "tok_visa", "billing_account": billing_account.public_id,},
        format="json",
    )
    assert sub_mock.return_value.update.call_count == 1
    assert resp.status_code == 201
    assert billing_account.customer.can_charge() is True


@pytest.mark.vcr()
@patch("djstripe.models.Customer.subscription", new_callable=PropertyMock)
@patch("djstripe.models.Customer.invoices", new_callable=PropertyMock)
def test_add_card_has_existing_subscription_past_due(
    invoices_mock, sub_mock, su_client
):
    billing = BillingAccountOwnerFactory(organization_user__seat_credits=0)
    billing_account: BillingAccount = billing.organization
    assert billing_account.customer is None

    sub_mock.return_value.status = SubscriptionStatus.unpaid
    invoices_mock.return_value = []
    resp = su_client.post(
        "/ww/api/payment_source/",
        {"stripe_token": "tok_visa", "billing_account": billing_account.public_id,},
        format="json",
    )
    assert invoices_mock.call_count == 1
    assert resp.status_code == 201
    assert billing_account.customer.can_charge() is True


@patch("djstripe.models.billing.Subscription.is_period_current")
@pytest.mark.vcr()
def test_new_signup_subscription_with_token(period_mock, su_client):
    billing = BillingAccountOwnerFactory(organization_user__seat_credits=0)
    billing_account: BillingAccount = billing.organization
    plan_one, plan_two = (
        PlanFactory(id="plan_GwOROprh1UPdQL"),  # Base Credits
        PlanFactory(id="plan_GwOvKvoNibwMK4"),  # Std Email Addon
    )
    plan_one.sync_from_stripe_data(plan_one.api_retrieve())
    plan_two.sync_from_stripe_data(plan_two.api_retrieve())
    plan_preset = WKPlanPresetFactory(stripe_plans_monthly=(plan_one, plan_two))

    assert billing_account.customer is None

    resp = su_client.post(
        f"/ww/api/billing_accounts/{billing_account.public_id}/subscription/",
        {
            "stripe_token": "tok_visa",
            "plan": plan_preset.public_id,
            "items": [
                {"stripe_id": plan_one.id, "quantity": 100,},
                {"stripe_id": plan_two.id, "quantity": 1,},
            ],
        },
        format="json",
    )
    assert resp.status_code == 201
    assert (
        resp.json()["url"]
        == f"http://testserver/ww/api/billing_accounts/{billing_account.public_id}/"
    )
    customer = billing_account.customer
    assert customer.can_charge() is True
    assert customer.has_active_subscription(plan_one)
    assert customer.has_active_subscription(plan_two)
    assert period_mock.call_count == 3  # 2 + 1 for is_valid in response body
    assert sorted(
        [
            item.plan.product.id
            for item in customer.subscription.items.select_related("plan__product")
        ]
    ) == sorted(["prod_Gw6HrLt8HOhTju", "prod_GwOi2Tcxvn2pi7"])


@pytest.mark.vcr()
def test_new_signup_subscription_without_token(su_client):
    billing = BillingAccountOwnerFactory(organization_user__seat_credits=0)
    billing_account: BillingAccount = billing.organization
    plan_one, plan_two = (
        PlanFactory(id="plan_GwOROprh1UPdQL"),  # Base Credits
        PlanFactory(id="plan_GwOvKvoNibwMK4"),  # Std Email Addon
    )
    stripe_plans = (plan_one, plan_two)
    plan_one.sync_from_stripe_data(plan_one.api_retrieve())
    plan_two.sync_from_stripe_data(plan_two.api_retrieve())
    plan_preset = WKPlanPresetFactory(stripe_plans_monthly=stripe_plans)

    assert billing_account.customer is None

    resp = su_client.post(
        f"/ww/api/billing_accounts/{billing_account.public_id}/subscription/",
        {
            "plan": plan_preset.public_id,
            "items": [
                {"stripe_id": plan_one.id, "quantity": 100,},
                {"stripe_id": plan_two.id, "quantity": 1,},
            ],
            "trial_days": 7,
        },
        format="json",
    )
    assert resp.status_code == 201
    assert (
        resp.json()["url"]
        == f"http://testserver/ww/api/billing_accounts/{billing_account.public_id}/"
    )
    customer = billing_account.customer
    assert customer.can_charge() is False
    assert sorted(
        [
            item.plan.product.id
            for item in customer.subscription.items.select_related("plan__product")
        ]
    ) == sorted(["prod_Gw6HrLt8HOhTju", "prod_GwOi2Tcxvn2pi7"])


@patch("djstripe.models.billing.Subscription.is_period_current")
@pytest.mark.vcr()
def test_upgrade_subscription(period_mock, su_client):
    billing = BillingAccountOwnerFactory(organization_user__seat_credits=0)
    billing_account: BillingAccount = billing.organization
    plan_one, plan_two, plan_three = (
        PlanFactory(id="plan_GwOROprh1UPdQL"),  # Base Credits
        PlanFactory(id="plan_GwOvKvoNibwMK4"),  # Std Email Addon
        PlanFactory(id="plan_GwOz3bLvfz05aL"),  # Advanced Email Addon
    )
    plan_one.sync_from_stripe_data(plan_one.api_retrieve())
    plan_two.sync_from_stripe_data(plan_two.api_retrieve())
    plan_three.sync_from_stripe_data(plan_three.api_retrieve())
    base_credits_product = "prod_Gw6HrLt8HOhTju"
    email_std_product = "prod_GwOi2Tcxvn2pi7"
    email_adv_product = "prod_GwOiUYoDI3gJGX"
    plan_preset = WKPlanPresetFactory(stripe_plans_monthly=(plan_one, plan_two))
    plan_preset_upgrade = WKPlanPresetFactory(
        stripe_plans_monthly=(plan_one, plan_three)
    )
    resp = su_client.post(
        f"/ww/api/billing_accounts/{billing_account.public_id}/subscription/",
        {
            "stripe_token": "tok_visa",
            "plan": plan_preset.public_id,
            "items": [
                {"stripe_id": plan_one.id, "quantity": 100,},
                {"stripe_id": plan_two.id, "quantity": 1,},
            ],
        },
        format="json",
    )
    assert resp.status_code == 201
    customer = billing_account.customer
    assert customer.has_active_subscription(plan_one)
    assert customer.has_active_subscription(plan_two)
    assert sorted(
        [
            item.plan.product.id
            for item in customer.subscription.items.select_related("plan__product")
        ]
    ) == sorted([base_credits_product, email_std_product])

    upgrade = su_client.patch(
        f"/ww/api/billing_accounts/{billing_account.public_id}/subscription/",
        {
            "plan": plan_preset_upgrade.public_id,
            "items": [
                {"stripe_id": plan_one.id, "quantity": 100,},
                {"stripe_id": plan_three.id, "quantity": 1,},
            ],
        },
        format="json",
    )
    assert upgrade.status_code == 200
    customer = billing_account.customer
    customer.refresh_from_db()
    assert customer.has_active_subscription(plan_one)
    assert customer.has_active_subscription(plan_two) is False
    assert customer.has_active_subscription(plan_three)
    assert sorted(
        [
            item.plan.product.id
            for item in customer.subscription.items.select_related("plan__product")
        ]
    ) == sorted([base_credits_product, email_adv_product])


@patch("djstripe.models.billing.Subscription.is_period_current")
@pytest.mark.vcr()
def test_change_subscription_billing_cycle(period_mock, su_client):
    billing = BillingAccountOwnerFactory(organization_user__seat_credits=0)
    billing_account: BillingAccount = billing.organization
    monthly_one, monthly_two = (
        PlanFactory(id="plan_GwOROprh1UPdQL"),  # Base Credits
        PlanFactory(id="plan_GwOvKvoNibwMK4"),  # Std Email Addon
    )
    yearly_one, yearly_two = (
        PlanFactory(id="plan_GwOabJCCxbWXI4"),  # Base Credits
        PlanFactory(id="plan_GwOvSu4wEolMqF"),  # Std Email Addon
    )
    monthly_one.sync_from_stripe_data(monthly_one.api_retrieve())
    monthly_two.sync_from_stripe_data(monthly_two.api_retrieve())
    yearly_one.sync_from_stripe_data(yearly_one.api_retrieve())
    yearly_two.sync_from_stripe_data(yearly_two.api_retrieve())

    base_credits_product = "prod_Gw6HrLt8HOhTju"
    email_std_product = "prod_GwOi2Tcxvn2pi7"
    monthly_preset = WKPlanPresetFactory(
        stripe_plans_monthly=(monthly_one, monthly_two)
    )
    yearly_preset = WKPlanPresetFactory(stripe_plans_yearly=(yearly_one, yearly_two))
    resp = su_client.post(
        f"/ww/api/billing_accounts/{billing_account.public_id}/subscription/",
        {
            "stripe_token": "tok_visa",
            "plan": monthly_preset.public_id,
            "items": [
                {"stripe_id": monthly_one.id, "quantity": 100,},
                {"stripe_id": monthly_two.id, "quantity": 1,},
            ],
        },
        format="json",
    )
    assert resp.status_code == 201
    customer = billing_account.customer
    assert customer.has_active_subscription(monthly_one)
    assert customer.has_active_subscription(monthly_two)
    assert sorted(
        [
            item.plan.product.id
            for item in customer.subscription.items.select_related("plan__product")
        ]
    ) == sorted([base_credits_product, email_std_product])

    upgrade = su_client.patch(
        f"/ww/api/billing_accounts/{billing_account.public_id}/subscription/",
        {
            "plan": yearly_preset.public_id,
            "items": [
                {"stripe_id": yearly_one.id, "quantity": 100,},
                {"stripe_id": yearly_two.id, "quantity": 1,},
            ],
        },
        format="json",
    )
    assert upgrade.status_code == 200
    customer = billing_account.customer
    assert customer.has_active_subscription(yearly_one)
    assert customer.has_active_subscription(yearly_two)
    assert sorted(
        [
            item.plan.product.id
            for item in customer.subscription.items.select_related("plan__product")
        ]
    ) == sorted([base_credits_product, email_std_product])


@patch("djstripe.models.billing.Subscription.is_period_current")
@pytest.mark.vcr()
def test_upgrade_subscription_quantity(period_mock, su_client):
    billing = BillingAccountOwnerFactory(organization_user__seat_credits=0)
    billing_account: BillingAccount = billing.organization
    plan_one, plan_two = (
        PlanFactory(id="plan_GwOROprh1UPdQL"),  # Base Credits
        PlanFactory(id="plan_GwOvKvoNibwMK4"),  # Std Email Addon
    )
    plan_one.sync_from_stripe_data(plan_one.api_retrieve())
    plan_two.sync_from_stripe_data(plan_two.api_retrieve())
    plan_preset = WKPlanPresetFactory(stripe_plans_monthly=(plan_one, plan_two))

    resp = su_client.post(
        f"/ww/api/billing_accounts/{billing_account.public_id}/subscription/",
        {
            "stripe_token": "tok_visa",
            "plan": plan_preset.public_id,
            "items": [
                {"stripe_id": plan_one.id, "quantity": 100,},
                {"stripe_id": plan_two.id, "quantity": 1,},
            ],
        },
        format="json",
    )
    assert resp.status_code == 201
    customer = billing_account.customer
    assert customer.has_active_subscription(plan_one)
    assert customer.has_active_subscription(plan_two)
    assert sorted(
        [item.quantity for item in customer.subscription.items.all()]
    ) == sorted([1, 100])

    upgrade = su_client.patch(
        f"/ww/api/billing_accounts/{billing_account.public_id}/subscription/",
        {
            "plan": plan_preset.public_id,
            "items": [
                {"stripe_id": plan_one.id, "quantity": 1000,},
                {"stripe_id": plan_two.id, "quantity": 1,},
            ],
        },
        format="json",
    )
    assert upgrade.status_code == 200
    customer = billing_account.customer
    customer.refresh_from_db()
    assert customer.has_active_subscription(plan_one)
    assert customer.has_active_subscription(plan_two)
    assert sorted(
        [item.quantity for item in customer.subscription.items.all()]
    ) == sorted([1, 1000])
