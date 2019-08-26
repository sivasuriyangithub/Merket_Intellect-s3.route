from factory import DjangoModelFactory, SubFactory

from whoweb.search.models import SearchExport
from whoweb.users.tests.factories import UserFactory


class SearchExportFactory(DjangoModelFactory):
    user = SubFactory(UserFactory)

    class Meta:
        model = SearchExport
