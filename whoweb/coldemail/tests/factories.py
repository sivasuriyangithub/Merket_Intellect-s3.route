from factory import (
    DjangoModelFactory,
    SubFactory,
    LazyAttribute,
)
from faker import Faker as NonFactoryFaker

from whoweb.coldemail.models import CampaignMessage, CampaignList, ColdCampaign
from whoweb.payments.tests.factories import BillingAccountMemberFactory
from whoweb.search.tests.factories import SearchExportFactory

fake = NonFactoryFaker()


class CampaignListFactory(DjangoModelFactory):
    seat = LazyAttribute(lambda o: BillingAccountMemberFactory().seat)
    export = SubFactory(SearchExportFactory)

    class Meta:
        model = CampaignList


class CampaignMessageFactory(DjangoModelFactory):
    seat = LazyAttribute(lambda o: BillingAccountMemberFactory().seat)

    class Meta:
        model = CampaignMessage


class ColdCampaignFactory(DjangoModelFactory):
    seat = LazyAttribute(lambda o: BillingAccountMemberFactory().seat)
    campaign_list = SubFactory(CampaignListFactory)
    message = SubFactory(CampaignMessageFactory)

    class Meta:
        model = ColdCampaign
