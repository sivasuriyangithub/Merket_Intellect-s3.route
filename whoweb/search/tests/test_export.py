import re
from unittest.mock import patch, Mock

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
    export: SearchExport = SearchExportFactory(query=query)
    export._set_columns()
    assert export.columns == cols


def test_export_set_columns_for_upload(query_contact_invites):
    export: SearchExport = SearchExportFactory(
        query=query_contact_invites, uploadable=True
    )
    export._set_columns()
    assert (
        export.columns
        == SearchExport.INTRO_COLS
        + SearchExport.BASE_COLS
        + SearchExport.DERIVATION_COLS
        + SearchExport.UPLOADABLE_COLS
    )


@pytest.mark.parametrize("skip,limit,target", [(0, 100, 100), (10, 20, 10)])
def test_export_set_target(query_contact_invites, skip, limit, target):
    query_contact_invites["filters"]["skip"] = skip
    query_contact_invites["filters"]["limit"] = limit
    export: SearchExport = SearchExportFactory(query=query_contact_invites)
    assert export.target == 0
    export._set_target()
    assert export.target == target


def test_export_set_target_from_profile_ids(query_specified_profiles_in_filters):
    export: SearchExport = SearchExportFactory(
        query=query_specified_profiles_in_filters
    )
    assert export.target == 0
    export._set_target()
    assert export.target == 11


@pytest_parametrize_plus(
    "q,progress,needed",
    [
        (fixture_ref("query_contact_invites"), 0, 26000),
        (fixture_ref("query_contact_invites"), 1000, 20800),
        (fixture_ref("query_no_contact"), 0, 5000),
        (fixture_ref("query_no_contact"), 1000, 4000),
    ],
)
def test_num_ids_needed(q, progress, needed):
    export: SearchExport = SearchExportFactory(
        query=q, progress_counter=progress, target=5000
    )
    assert export.num_ids_needed == needed


@pytest_parametrize_plus(
    "q,progress,skip,start_at",
    [
        (fixture_ref("query_contact_invites"), 0, 0, 0),
        (fixture_ref("query_contact_invites"), 0, 100, 520),
        (fixture_ref("query_contact_invites"), 100, 100, 1040),
        (fixture_ref("query_no_contact"), 0, 0, 0),
        (fixture_ref("query_no_contact"), 0, 100, 100),
        (fixture_ref("query_no_contact"), 100, 100, 200),
    ],
)
def test_start_from_count(q, progress, skip, start_at):
    q["filters"]["skip"] = skip
    export: SearchExport = SearchExportFactory(query=q, progress_counter=progress)
    assert export.start_from_count == start_at


def test_get_column_names(user_facing_column_headers):
    export: SearchExport = SearchExportFactory(
        columns=SearchExport.BASE_COLS + SearchExport.DERIVATION_COLS
    )
    assert export.get_column_names() == user_facing_column_headers


def test_get_column_names_for_uploadable(all_uploadable_column_headers):
    export: SearchExport = SearchExportFactory(
        uploadable=True,
        columns=SearchExport.INTRO_COLS
        + SearchExport.BASE_COLS
        + SearchExport.DERIVATION_COLS
        + SearchExport.UPLOADABLE_COLS,
    )
    assert export.get_column_names() == all_uploadable_column_headers


def test_ensure_search_interface(query_contact_invites):
    export: SearchExport = SearchExportFactory(query=query_contact_invites)
    assert export.scroll is None
    export.ensure_search_interface()
    assert export.scroll is not None
    old_scroll_key = export.scroll.scroll_key
    export.ensure_search_interface()
    assert old_scroll_key == export.scroll.scroll_key
    export.ensure_search_interface(force=True)
    assert old_scroll_key != export.scroll.scroll_key


@pytest.mark.parametrize(
    "target,charged,progress,refund",
    [(1000, 1000, 999, 1), (1010, 1000, 1000, 10), (1000, 1000, 1000, 0)],
)
def test_do_post_pages_completion(target, charged, progress, refund):
    export: SearchExport = SearchExportFactory(
        target=target, charged=charged, progress_counter=progress, charge=True
    )
    export.do_post_pages_completion()
    export.refresh_from_db()
    assert export.refunded == refund
    assert export.charged == charged - refund
    assert export.seat.billing.seat_credits == refund
    assert export.status == "4"


@pytest.mark.parametrize(
    "charged,valid,starting_refund,this_refund",
    [(1000, 200, 100, 800), (1000, 0, 0, 1000), (990, 990, 10, 0)],
)
@patch("whoweb.search.models.SearchExport.return_validation_results_to_cache")
@patch("whoweb.search.models.SearchExport.get_validation_results")
def test_do_post_validation_completion(
    get_validation_results, cache_mock, charged, valid, starting_refund, this_refund
):
    export: SearchExport = SearchExportFactory(
        charged=charged, refunded=starting_refund, charge=True
    )
    get_validation_results.return_value = [True] * valid
    export.do_post_validation_completion()
    assert cache_mock.call_count == 1
    export.refresh_from_db()
    assert export.refunded == starting_refund + this_refund
    assert export.charged == charged - this_refund
    assert export.valid_count == charged - this_refund
    assert export.seat.billing.seat_credits == this_refund  # factory default creds == 0
    assert export.status == "16"


def test_upload_validation():
    export: SearchExport = SearchExportFactory()
    assert export.upload_validation() is None
    assert export.status == 8
    assert export.validation_list_id == SearchExport.SKIP_CODE


def test_get_validation_status(requests_mock):
    LIST_ID = "1"
    export: SearchExport = SearchExportFactory(validation_list_id=LIST_ID)
    requests_mock.register_uri(
        "GET",
        f"https://dv3.datavalidation.com/api/v2/user/me/list/{LIST_ID}/",
        json={"status_value": "SUCCESS", "status_percent_complete": 100},
    )
    requests_mock.register_uri(
        "HEAD",
        f"https://dv3.datavalidation.com/api/v2/user/me/list/{LIST_ID}/download_result/",
    )
    requests_mock.register_uri(
        "GET",
        f"https://dv3.datavalidation.com/api/v2/user/me/list/{LIST_ID}/download_result/",
    )
    assert export.get_validation_status() is True


def test_get_validation_status_not_done(requests_mock):
    LIST_ID = "1"
    export: SearchExport = SearchExportFactory(validation_list_id=LIST_ID)
    requests_mock.register_uri(
        "GET",
        f"https://dv3.datavalidation.com/api/v2/user/me/list/{LIST_ID}/",
        json={"status_value": "SUCCESS", "status_percent_complete": 90},
    )
    assert export.get_validation_status() is False


def test_get_validation_status_failed(requests_mock):
    LIST_ID = "1"
    export: SearchExport = SearchExportFactory(validation_list_id=LIST_ID)
    requests_mock.register_uri(
        "GET",
        f"https://dv3.datavalidation.com/api/v2/user/me/list/{LIST_ID}/",
        json={"status_value": "FAILED", "status_percent_complete": 100},
    )
    assert export.get_validation_status() is False


def test_get_validation_status_file_missing(requests_mock):
    LIST_ID = "1"
    export: SearchExport = SearchExportFactory(validation_list_id=LIST_ID)
    requests_mock.register_uri(
        "GET",
        f"https://dv3.datavalidation.com/api/v2/user/me/list/{LIST_ID}/",
        json={"status_value": "SUCCESS", "status_percent_complete": 100},
    )
    requests_mock.register_uri(
        "HEAD",
        f"https://dv3.datavalidation.com/api/v2/user/me/list/{LIST_ID}/download_result/",
        status_code=404,
    )
    assert export.get_validation_status() is False


@patch("requests_cache.CachedSession.get")
def test_get_validation_status_file_error(get_mock, requests_mock):
    LIST_ID = "1"
    export: SearchExport = SearchExportFactory(validation_list_id=LIST_ID)
    requests_mock.register_uri(
        "GET",
        f"https://dv3.datavalidation.com/api/v2/user/me/list/{LIST_ID}/",
        json={"status_value": "SUCCESS", "status_percent_complete": 100},
    )
    requests_mock.register_uri(
        "HEAD",
        f"https://dv3.datavalidation.com/api/v2/user/me/list/{LIST_ID}/download_result/",
    )
    get_mock.return_value = Mock(ok="mystatus")
    assert export.get_validation_status() is "mystatus"


def test_get_named_fetch_url():
    export: SearchExport = SearchExportFactory()
    assert (
        export.get_named_fetch_url()
        == f"/ww/search/exports/{str(export.uuid)}/download/{str(export.uuid)}__fetch.csv"
    )


def test_get_absolute_url():
    export: SearchExport = SearchExportFactory()
    assert (
        export.get_absolute_url()
        == f"/ww/search/exports/{str(export.uuid)}/download/results.csv"
    )
