from factory import DjangoModelFactory, SubFactory, Sequence, LazyAttribute, Iterator

from whoweb.payments.tests.factories import BillingAccountMemberFactory
from whoweb.search.models import SearchExport
from whoweb.search.models.export import SearchExportPage
from whoweb.search.tests.fixtures import done


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
