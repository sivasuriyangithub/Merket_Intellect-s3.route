from typing import Type, TypeVar

from django.utils.timezone import now
from factory import (
    DjangoModelFactory,
    SubFactory,
    LazyAttribute,
    RelatedFactory,
    Sequence,
    SelfAttribute,
    post_generation,
)
from factory.fuzzy import FuzzyInteger
from faker import Faker as NonFactoryFaker
from faker.providers import internet

from whoweb.campaigns.models.base import BaseCampaignRunner, SendingRule, DripRecord
from whoweb.coldemail.tests.factories import CampaignMessageFactory, ColdCampaignFactory
from whoweb.payments.tests.factories import BillingAccountMemberFactory

fake = NonFactoryFaker()
fake.add_provider(internet)


class CampaignRunnerFactory(DjangoModelFactory):
    seat = LazyAttribute(lambda o: BillingAccountMemberFactory().seat)
    budget = FuzzyInteger(low=100, high=10000)

    class Meta:
        model = BaseCampaignRunner


class SendingRuleFactory(DjangoModelFactory):
    class Meta:
        model = SendingRule

    runner = SubFactory(CampaignRunnerFactory)
    message = SubFactory(CampaignMessageFactory)
    index = Sequence(int)
    send_datetime = LazyAttribute(lambda o: now() if o.index == 0 else None)


class DripRecordFactory(DjangoModelFactory):
    class Meta:
        model = DripRecord

    runner = SubFactory(CampaignRunnerFactory)
    drip = SubFactory(ColdCampaignFactory)
    root = SubFactory(ColdCampaignFactory)
    order = Sequence(int)


class CampaignRunnerWithMessagesFactory(CampaignRunnerFactory):
    msg0 = RelatedFactory(SendingRuleFactory, "runner")
    msg1 = RelatedFactory(SendingRuleFactory, "runner")
    msg2 = RelatedFactory(SendingRuleFactory, "runner")

    class Meta:
        model = BaseCampaignRunner


class CampaignRunnerWithDripsFactory(CampaignRunnerFactory):
    msg0 = RelatedFactory(SendingRuleFactory, "runner")
    msg1 = RelatedFactory(SendingRuleFactory, "runner")
    msg2 = RelatedFactory(SendingRuleFactory, "runner")
    drip1 = RelatedFactory(DripRecordFactory, "runner")
    drip2 = RelatedFactory(DripRecordFactory, "runner")

    @post_generation
    def campaigns(self, create, extracted, **kwargs):
        root = ColdCampaignFactory(message=self.messages.all()[0])
        self.campaigns.add(root)
        d0 = self.drips.all()[0]
        d0.message = self.messages.all()[1]
        d0.root = root
        d0.save()
        d1 = self.drips.all()[1]
        d1.message = self.messages.all()[2]
        d1.root = root
        d1.save()

    class Meta:
        model = BaseCampaignRunner
