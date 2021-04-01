import pytest

from whoweb.payments.models import BillingAccount, WKPlanPreset
from whoweb.payments.tests.factories import (
    WKPlanFactory,
    BillingAccountOwnerFactory,
    WKPlanPresetFactory,
)
from whoweb.search.models.profile import GradedPhone
from whoweb.search.tests.factories import ResultProfileFactory, GradedEmailFactory

pytestmark = pytest.mark.django_db


def test_charges_work():
    plan = WKPlanFactory()
    profile = ResultProfileFactory(
        graded_emails=[GradedEmailFactory(email="passing@whoknows.com", grade="A+")]
    )
    assert plan.compute_contact_credit_use(profile) == 100


def test_charges_personal():
    plan = WKPlanFactory()
    profile = ResultProfileFactory(
        graded_emails=[GradedEmailFactory(email="passing@aol.com", grade="A+")]
    )
    assert plan.compute_contact_credit_use(profile) == 200


def test_charges_work_and_personal():
    plan = WKPlanFactory()
    profile = ResultProfileFactory(
        graded_emails=[
            GradedEmailFactory(email="passing@aol.com", grade="A+"),
            GradedEmailFactory(email="passing@acme.com", grade="B+"),
        ]
    )
    assert plan.compute_contact_credit_use(profile) == 300


def test_charges_work_and_personal_and_phone():
    plan = WKPlanFactory()
    profile = ResultProfileFactory(
        graded_emails=[
            GradedEmailFactory(email="passing@aol.com", grade="A+"),
            GradedEmailFactory(email="passing@acme.com", grade="B+"),
        ],
        graded_phones=[GradedPhone(number="1")],
    )
    assert plan.compute_contact_credit_use(profile) == 700


def test_charges_phone():
    plan = WKPlanFactory()
    profile = ResultProfileFactory(
        graded_phones=[GradedPhone(number="1")], graded_emails=[]
    )
    assert plan.compute_contact_credit_use(profile) == 400


def test_plan_preset_creates_plan():
    plan_preset: WKPlanPreset = WKPlanPresetFactory()
    plan = plan_preset.create()
    assert plan_preset.permission_group == plan.permission_group
    assert plan_preset.credits_per_phone == plan.credits_per_phone
    assert plan_preset.credits_per_work_email == plan.credits_per_work_email
    assert plan_preset.credits_per_personal_email == plan.credits_per_personal_email
    assert plan_preset.credits_per_enrich == plan.credits_per_enrich
    assert plan_preset.marketing_name == plan.marketing_name


def test_expire_all_remaining_credits(su):
    billing_owner = BillingAccountOwnerFactory(
        organization_user__seat_credits=100,
        organization_user__pool_credits=False,
        organization_user__organization__credit_pool=500,
    )
    billing_member = billing_owner.organization_user
    billing_account: BillingAccount = billing_owner.organization

    assert billing_member.credits == 100
    assert billing_account.credit_pool == 500
    billing_account.expire_all_remaining_credits(initiated_by=su)
    billing_member.refresh_from_db()
    billing_account.refresh_from_db()
    assert billing_member.credits == 0
    assert billing_account.credits == 0
