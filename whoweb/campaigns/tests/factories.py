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


class CampaignRunnerWithDripsFactory(CampaignRunnerWithMessagesFactory):
    root = SubFactory(ColdCampaignFactory, message=SelfAttribute("..msg0"))
    drip1 = RelatedFactory(
        DripRecordFactory,
        "runner",
        root=SelfAttribute("..root"),
        drip__message=SelfAttribute("..msg1"),
    )
    drip2 = RelatedFactory(
        DripRecordFactory,
        "runner",
        root=SelfAttribute("..root"),
        drip__message=SelfAttribute("..msg2"),
    )

    @post_generation
    def campaigns(self, create, extracted, **kwargs):
        if not create:
            self.campaigns.add(self.root)
            return
        return super().post_generation(create, extracted, **kwargs)
