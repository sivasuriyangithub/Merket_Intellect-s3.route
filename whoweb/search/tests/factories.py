from factory import (
    DjangoModelFactory,
    SubFactory,
    Sequence,
    LazyAttribute,
    Iterator,
    Factory,
    Faker,
    List,
)
from faker import Faker as NonFactoryFaker
from faker.providers import internet

from whoweb.payments.tests.factories import BillingAccountMemberFactory
from whoweb.search.models import SearchExport, ResultProfile
from whoweb.search.models.export import SearchExportPage
from whoweb.search.models.profile import GradedEmail
from whoweb.search.tests.fixtures import done

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


class GradedEmailFactory(Factory):
    email = fake.email()
    grade = "F"

    class Meta:
        model = GradedEmail


class ResultProfileFactory(Factory):
    _id = Sequence(str)
    first_name = Faker("first_name")
    last_name = Faker("last_name")
    email = "passing@email.com"
    grade = "A+"
    emails = List(["passing@email.com", fake.email(), fake.email()])
    graded_emails = List(
        [
            SubFactory(GradedEmailFactory, email="passing@email.com", grade="A+"),
            SubFactory(GradedEmailFactory),
        ]
    )

    class Meta:
        model = ResultProfile
