from factory import (
    DjangoModelFactory,
    SubFactory,
    LazyAttribute,
)
from faker import Faker as NonFactoryFaker

from whoweb.coldemail.models import (
    CampaignMessage,
    CampaignMessageTemplate,
    CampaignList,
    ColdCampaign,
    SingleColdEmail,
)
from whoweb.payments.tests.factories import BillingAccountMemberFactory
from whoweb.search.tests.factories import SearchExportFactory

fake = NonFactoryFaker()
fake.add_provider("date_time")


class CampaignListFactory(DjangoModelFactory):
    seat = LazyAttribute(lambda o: BillingAccountMemberFactory().seat)
    export = SubFactory(SearchExportFactory)

    class Meta:
        model = CampaignList


class CampaignMessageFactory(DjangoModelFactory):
    seat = LazyAttribute(lambda o: BillingAccountMemberFactory().seat)

    class Meta:
        model = CampaignMessage


class CampaignMessageTemplateFactory(DjangoModelFactory):
    seat = LazyAttribute(lambda o: BillingAccountMemberFactory().seat)

    class Meta:
        model = CampaignMessageTemplate


class ColdCampaignFactory(DjangoModelFactory):
    seat = LazyAttribute(lambda o: BillingAccountMemberFactory().seat)
    campaign_list = SubFactory(CampaignListFactory)
    message = SubFactory(CampaignMessageFactory)

    class Meta:
        model = ColdCampaign


class SingleColdEmailFactory(DjangoModelFactory):
    seat = LazyAttribute(lambda o: BillingAccountMemberFactory().seat)
    message = SubFactory(CampaignMessageFactory)
    send_date = fake.future_date(end_date="+30d", tzinfo=None)

    class Meta:
        model = SingleColdEmail
