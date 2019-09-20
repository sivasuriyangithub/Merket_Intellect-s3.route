from factory import DjangoModelFactory, SubFactory, SelfAttribute, Faker

from whoweb.payments.models import (
    BillingAccountMember,
    BillingAccount,
    BillingAccountOwner,
)
from whoweb.users.tests.factories import SeatFactory


class BillingAccountFactory(DjangoModelFactory):

    name = Faker("company")
    group = SelfAttribute("..seat.organization")

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
