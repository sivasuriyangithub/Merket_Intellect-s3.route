from factory import DjangoModelFactory, SubFactory

from whoweb.search.models import SearchExport
from whoweb.users.tests.factories import UserFactory, SeatFactory


class SearchExportFactory(DjangoModelFactory):
    seat = SubFactory(SeatFactory)

    class Meta:
        model = SearchExport
