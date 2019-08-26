from unittest.mock import patch

import pytest
from django.conf import settings
from django.db import transaction

from whoweb.search.models import SearchExport
from whoweb.search.tests.factories import SearchExportFactory

pytestmark = pytest.mark.django_db(transaction=True)


def validation_result_generator():
    results = [
        ("a@a.com", "wp:1", "A"),
        ("b@b.com", "wp:2", "B"),
        ("c@c.com", "wp:3", "C"),
        ("d@d.com", "wp:4", "D"),
        ("f@af.com", "wp:5", "F"),
    ] * 101
    for row in results:
        yield {"email": row[0], "profile_id": row[1], "grade": row[2]}


@patch("whoweb.core.router.Router.update_validations")
@patch(
    "whoweb.search.models.SearchExport.get_validation_results",
    side_effect=validation_result_generator,
)
def test_return_validation_results_to_cache(result_mock, cache_mock):
    export: SearchExport = SearchExportFactory()
    export.return_validation_results_to_cache()
    assert cache_mock.call_count == 3  # (250, 250, 5)


@patch("whoweb.search.models.SearchExport._generate_pages")
@pytest.mark.django_db(transaction=False)
def test_generate_pages_in_serial_ok(gen_mock):
    export: SearchExport = SearchExportFactory()
    with transaction.atomic():
        res = e.generate_pages()
        assert res is not None
    with transaction.atomic():
        e = SearchExport.objects.get(pk=export.pk)
        res = export.generate_pages()
        assert res is not None

    assert gen_mock.call_count == 2


@patch("whoweb.search.models.SearchExport._generate_pages")
@pytest.mark.django_db(transaction=False)
def test_generate_pages_in_serial_fails_quietly(gen_mock):
    export: SearchExport = SearchExportFactory()
    with transaction.atomic():
        e = SearchExport.objects.get(pk=export.pk)
        res = e.generate_pages()
        assert res is not None
        with transaction.atomic():
            e = SearchExport.objects.get(pk=export.pk)
            res = e.generate_pages()
            assert res is None

    assert gen_mock.call_count == 1
