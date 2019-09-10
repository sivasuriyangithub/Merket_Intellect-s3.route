from unittest.mock import patch

import pytest

from whoweb.search.models import SearchExport
from whoweb.search.tests.factories import SearchExportFactory

pytestmark = pytest.mark.django_db


def validation_result_generator(only_valid=True):
    results = [
        ("a@a.com", "wp:1", "A"),
        ("b@b.com", "wp:2", "B"),
        ("c@c.com", "wp:3", "C"),
        ("d@d.com", "wp:4", "D"),
        ("f@af.com", "wp:5", "F"),
    ] * 101
    for row in results:
        if only_valid and row[2][0] not in ["A", "B"]:
            continue
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


# def test_create_from_query()
#     User
