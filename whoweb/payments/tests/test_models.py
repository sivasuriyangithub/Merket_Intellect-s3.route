import pytest
from whoweb.payments.tests.factories import WKPlanFactory
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
