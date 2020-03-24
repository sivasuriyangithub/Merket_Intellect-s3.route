import factory
from djstripe.models import Plan
from factory import DjangoModelFactory, SubFactory, SelfAttribute, Faker, RelatedFactory

from whoweb.payments.models import (
    BillingAccountMember,
    BillingAccount,
    BillingAccountOwner,
    WKPlan,
    WKPlanPreset,
)
from whoweb.users.tests.factories import SeatFactory


class WKPlanFactory(DjangoModelFactory):
    credits_per_enrich = 100
    credits_per_work_email = 100
    credits_per_personal_email = 200
    credits_per_phone = 400

    class Meta:
        model = WKPlan


class PlanFactory(DjangoModelFactory):
    id = Faker("slug")
    active = True

    class Meta:
        model = Plan


class WKPlanPresetFactory(DjangoModelFactory):
    credits_per_enrich = 100
    credits_per_work_email = 100
    credits_per_personal_email = 200
    credits_per_phone = 400

    class Meta:
        model = WKPlanPreset

    @factory.post_generation
    def stripe_plans(self, create, extracted, **kwargs):
        if not create:
            # Simple build, do nothing.
            return

        if extracted:
            # A list of groups were passed in, use them
            for plan in extracted:
                self.stripe_plans.add(plan)


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
