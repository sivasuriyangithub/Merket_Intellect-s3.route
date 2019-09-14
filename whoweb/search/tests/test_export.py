from unittest.mock import patch

import pytest
from pytest_cases import fixture_ref, pytest_parametrize_plus

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


@pytest_parametrize_plus(
    "query,cols",
    [
        (fixture_ref("query_no_contact"), SearchExport.BASE_COLS),
        (
            fixture_ref("query_contact_no_invites"),
            SearchExport.BASE_COLS + SearchExport.DERIVATION_COLS,
        ),
        (
            fixture_ref("query_contact_invites"),
            SearchExport.INTRO_COLS
            + SearchExport.BASE_COLS
            + SearchExport.DERIVATION_COLS,
        ),
    ],
)
def test_export_set_columns(query, cols):
    export = SearchExportFactory(query=query)
    export._set_columns()
    assert export.columns == cols


def test_export_set_columns_for_upload(query_contact_invites):
    export = SearchExportFactory(query=query_contact_invites, uploadable=True)
    export._set_columns()
    assert (
        export.columns
        == SearchExport.INTRO_COLS
        + SearchExport.BASE_COLS
        + SearchExport.DERIVATION_COLS
        + SearchExport.UPLOADABLE_COLS
    )
