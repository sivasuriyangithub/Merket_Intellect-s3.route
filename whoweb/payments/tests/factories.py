from factory import DjangoModelFactory, SubFactory, SelfAttribute, Faker

from whoweb.payments.models import (
    BillingAccountMember,
    BillingAccount,
    BillingAccountOwner,
    WKPlan,
)
from whoweb.users.tests.factories import SeatFactory


class WKPlanFactory(DjangoModelFactory):
    credits_per_enrich = 100
    credits_per_work_email = 100
    credits_per_personal_email = 200
    credits_per_phone = 400

    class Meta:
        model = WKPlan


class BillingAccountFactory(DjangoModelFactory):

    name = Faker("company")
    group = SelfAttribute("..seat.organization")
    plan = SubFactory(WKPlanFactory)

    class Meta:
        model = BillingAccount


class BillingAccountMemberFactory(DjangoModelFactory):
    seat = SubFactory(SeatFactory)
    user = SelfAttribute("seat.user")
    organization = SubFactory(BillingAccountFactory)

    class Meta:
        model = BillingAccountMember


class BillingAccountOwnerFactory(DjangoModelFactory):

    organization_user = SubFactory(BillingAccountMemberFactory)
    organization = SelfAttribute("organization_user.organization")

    class Meta:
        model = BillingAccountOwner
