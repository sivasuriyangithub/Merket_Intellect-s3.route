from factory import (
    DjangoModelFactory,
    SubFactory,
    Sequence,
    LazyAttribute,
    Iterator,
    Factory,
    Faker,
    Dict,
    List,
    SelfAttribute,
)
from faker import Faker as NonFactoryFaker
from whoweb.payments.tests.factories import BillingAccountMemberFactory
from whoweb.search.models import SearchExport, ResultProfile
from whoweb.search.models.export import SearchExportPage
from whoweb.search.tests.fixtures import done
from faker.providers import internet

fake = NonFactoryFaker()
fake.add_provider(internet)


class SearchExportFactory(DjangoModelFactory):
    seat = LazyAttribute(lambda o: BillingAccountMemberFactory().seat)

    class Meta:
        model = SearchExport


class SearchExportPageFactory(DjangoModelFactory):
    export = SubFactory(SearchExportFactory)
    page_num = Sequence(lambda n: n)
    data = Iterator([done, done, done, done, done])

    class Meta:
        model = SearchExportPage


class ResultProfileFactory(Factory):

    _id = Sequence(str)
    first_name = Faker("first_name")
    last_name = Faker("last_name")
    derived_contact = Dict(
        dict(
            email="passing@email.com",
            emails=List(["passing@email.com", fake.email(), fake.email()]),
            _graded_emails=List(
                [
                    Dict({"email": "passing@email.com", "grade": "A+"}),
                    Dict({"email": fake.email(), "grade": "F"}),
                ]
            ),
        )
    )

    class Meta:
        model = ResultProfile
