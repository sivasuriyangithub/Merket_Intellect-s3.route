import types
from unittest.mock import patch

import pytest
from celery import chord

from whoweb.search.models import SearchExport, ResultProfile
from whoweb.search.models.export import SearchExportPage
from whoweb.search.models.profile import VALIDATED
from whoweb.search.tests.factories import (
    SearchExportFactory,
    SearchExportPageFactory,
    ResultProfileFactory,
)

pytestmark = pytest.mark.django_db

scroll_effect = [
    ["wp:1", "wp:2", "wp:3", "wp:4", "wp:5"],
    ["wp:6", "wp:7", "wp:8", "wp:9", "wp:10"],
    ["wp:11", "wp:12", "wp:13", "wp:14", "wp:15"],
    ["wp:16", "wp:17", "wp:18", "wp:19"],
    [],
]


def test_generate_pages_specified(query_specified_profiles_in_filters):
    export: SearchExport = SearchExportFactory(
        query=query_specified_profiles_in_filters
    )
    export._set_target()
    export._generate_pages()
    assert export.pages.count() == 1
    export._generate_pages()
    assert export.pages.count() == 1


@pytest.mark.parametrize("population,pages", [(100, 1), (500, 2), (601, 3)])
@patch("whoweb.search.models.ScrollSearch.get_ids_for_page")
@patch("whoweb.search.models.ScrollSearch.population")
def test_generate_pages(pop_mock, get_ids, query_contact_invites, population, pages):
    pop_mock.return_value = population
    export: SearchExport = SearchExportFactory(query=query_contact_invites)
    export._set_target()
    export._generate_pages()
    assert get_ids.call_count == pages
    assert export.pages.count() == pages


@pytest.mark.parametrize("population,pages", [(100, 1), (500, 2), (601, 3)])
@patch("whoweb.search.models.ScrollSearch.get_profiles_for_page")
@patch("whoweb.search.models.ScrollSearch.get_ids_for_page")
@patch("whoweb.search.models.ScrollSearch.population")
def test_generate_pages_continuation(
    pop_mock, get_ids, get_page, query_contact_invites, population, pages
):
    pop_mock.return_value = population
    export: SearchExport = SearchExportFactory(query=query_contact_invites)
    export._set_target()
    export._generate_pages()
    assert export.pages.count() == pages
    export.pages.update(data={"done": True})
    export._generate_pages()
    assert export.pages.count() == pages * 2


@patch("whoweb.search.models.SearchExport._generate_pages")
def test_generate_export_public(private_mock, query_contact_invites):
    export: SearchExport = SearchExportFactory(query=query_contact_invites)
    assert export.generate_pages() == private_mock.return_value
    assert private_mock.call_count == 1
    export.refresh_from_db(fields=("status",))
    assert export.status == 2


@patch("whoweb.search.models.ScrollSearch.get_profiles_for_page")
@patch("whoweb.search.models.ScrollSearch.get_ids_for_page")
def test_page_process_no_derive(
    get_ids_mock,
    get_page_mock,
    query_no_contact,
    search_results,
    search_result_profiles,
):
    get_ids_mock.return_value = search_results
    get_page_mock.return_value = search_result_profiles
    export: SearchExport = SearchExportFactory(query=query_no_contact)
    export._set_target()
    export.ensure_search_interface()
    page: SearchExportPage = SearchExportPageFactory(export=export, data=None)

    assert page.data is None
    assert page.do_page_process() is None  # data direct
    page.refresh_from_db()
    assert page.data is not None
    export.refresh_from_db(fields=("progress_counter",))
    assert export.progress_counter == len(search_result_profiles)


def test_page_process_existing_data(query_no_contact, raw_derived):
    export: SearchExport = SearchExportFactory()
    pages: [SearchExportPage] = SearchExportPageFactory.create_batch(
        3, export=export, data=raw_derived
    )
    assert pages[0].do_page_process() is None
    export.refresh_from_db(fields=("progress_counter",))
    assert export.progress_counter == 0


@patch("whoweb.search.models.ScrollSearch.get_profiles_for_page")
def test_page_process_applies_group_derivations(
    get_profiles_mock, search_result_profiles, query_contact_invites
):
    get_profiles_mock.return_value = search_result_profiles
    export: SearchExport = SearchExportFactory(query=query_contact_invites)
    export._set_target()
    export.ensure_search_interface()
    pages: [SearchExportPage] = SearchExportPageFactory.create_batch(
        3, export=export, data=None
    )
    assert isinstance(pages[0].do_page_process(), chord)


def test_get_next_empty_page():
    export: SearchExport = SearchExportFactory()
    pages: [SearchExportPage] = SearchExportPageFactory.create_batch(
        3, export=export, data=None
    )
    assert list(export.get_next_empty_page()) == [pages[0]]
    SearchExportPage.objects.filter(pk=pages[0].pk).update(data={"done": True})
    assert list(export.get_next_empty_page()) == [pages[1]]


def test_get_next_empty_page_batch():
    export: SearchExport = SearchExportFactory()
    pages: [SearchExportPage] = SearchExportPageFactory.create_batch(
        20, export=export, data=None
    )
    first_set = export.get_next_empty_page(5)
    assert first_set.count() == 5
    second_obj_in_first_set = first_set[1]
    SearchExportPage.objects.filter(pk=pages[0].pk).update(data={"done": True})
    next_overlapping_set = export.get_next_empty_page(5)
    assert next_overlapping_set.count() == 5
    first_obj_in_second_set = next_overlapping_set[0]
    assert second_obj_in_first_set == first_obj_in_second_set


def test_get_raw_one_page(raw_derived):
    export: SearchExport = SearchExportFactory()
    SearchExportPageFactory.create_batch(
        1, export=export, count=len(raw_derived), data=raw_derived
    )
    raw = export.get_raw()
    assert isinstance(raw, types.GeneratorType)
    assert list(raw) == raw_derived


def test_get_raw_cursor(raw_derived):
    export: SearchExport = SearchExportFactory()
    SearchExportPageFactory.create_batch(
        100, export=export, count=len(raw_derived), data=raw_derived
    )
    raw = export.get_raw()
    assert isinstance(raw, types.GeneratorType)
    assert list(raw) == raw_derived * 100


def test_get_profiles(raw_derived):
    export: SearchExport = SearchExportFactory()
    profiles = export.get_profiles(raw=raw_derived)
    assert isinstance(profiles, types.GeneratorType)
    assert list(profiles)[0].email == "patrick@beast.vc"


@patch("whoweb.search.models.SearchExport.get_profiles")
def test_get_ungraded_email_rows(get_profile_mock, raw_derived):
    get_profile_mock.return_value = (
        ResultProfile.from_json(profile) for profile in raw_derived
    )
    export: SearchExport = SearchExportFactory()
    rows = export.get_ungraded_email_rows()
    assert isinstance(rows, types.GeneratorType)
    assert sorted(list(rows)) == sorted(
        [
            (
                "david.kearney@bipc.com",
                "wp:J8ccNBtnoJx35dznq6VunSi1zKiHX9xB2chdQ1tHuSa7",
            ),
            ("dkearney@bipc.com", "wp:J8ccNBtnoJx35dznq6VunSi1zKiHX9xB2chdQ1tHuSa7"),
            ("dsmiller@lmc.org", "wp:B7ufHbkfeYSjWV73BTAiWeuh1JELxH8rs2GV5GEa2yAG"),
            (
                "davidsmiller@topworkplaces.com",
                "wp:B7ufHbkfeYSjWV73BTAiWeuh1JELxH8rs2GV5GEa2yAG",
            ),
            (
                "juliecarmona@azalaw.com",
                "wp:GyvzBUofSuq6nYf5qA49giUskhMnWB9A8dXwWkDxFFah",
            ),
            ("jcarmona@abu.edu.ng", "wp:GyvzBUofSuq6nYf5qA49giUskhMnWB9A8dXwWkDxFFah"),
        ]
    )


@patch("whoweb.search.models.SearchExport.get_validation_results")
@patch("whoweb.search.models.SearchExport.get_profiles")
def test_generate_email_id_pairs(get_profile_mock, validation_mock, raw_derived):
    validation_mock.return_value = []
    get_profile_mock.return_value = (
        ResultProfile.from_json(profile) for profile in raw_derived
    )
    export: SearchExport = SearchExportFactory()
    rows = export.generate_email_id_pairs()
    assert isinstance(rows, types.GeneratorType)
    assert list(rows) == [
        ("patrick@beast.vc", "wp:4XJFtuYgV6ZU756WQH9n96K75EUZdZhbQ3Z5iDK7Wz97")
    ]


@patch("whoweb.core.router.Router.make_exportable_invite_key")
def test_get_csv_row(key_mock):
    export: SearchExport = SearchExportFactory()
    profile: ResultProfile = ResultProfileFactory(derivation_status=VALIDATED)
    key_mock.return_value = {"key": "invitation"}
    assert len(export.get_csv_row(profile)) == 10
    assert len(export.get_csv_row(profile, with_invite=True)) == 11
    assert export.get_csv_row(profile, with_invite=True)[0] == "invitation"
    row = export.get_csv_row(profile, enforce_valid_contact=True)
    assert row[9] == "passing@email.com"
    export.uploadable = True
    assert len(export.get_csv_row(profile)) == 12
    assert len(export.get_csv_row(profile, enforce_valid_contact=True)) == 30


@patch("whoweb.core.router.Router.make_exportable_invite_key")
@patch("whoweb.search.models.SearchExport.get_profiles")
def test_generate_csv_rows(get_profiles_mock, key_mock, query_contact_invites):
    export: SearchExport = SearchExportFactory(target=200, query=query_contact_invites)
    profiles: [ResultProfile] = ResultProfileFactory.create_batch(
        10, derivation_status=VALIDATED
    )
    get_profiles_mock.return_value = profiles
    csv = export.generate_csv_rows()
    assert isinstance(csv, types.GeneratorType)
    csv = list(csv)
    assert len(csv) == 11
    assert csv[0] == export.get_column_names()


def test_save_profile(result_profile_derived):
    page: SearchExportPage = SearchExportPageFactory()
    SearchExportPage.save_profile(page.pk, result_profile_derived)
    page.refresh_from_db()
    assert page.working_data == {
        result_profile_derived.id: result_profile_derived.to_json()
    }


def test_save_profile_idempotent(result_profile_derived):
    page: SearchExportPage = SearchExportPageFactory()
    SearchExportPage.save_profile(page.pk, result_profile_derived)
    SearchExportPage.save_profile(page.pk, result_profile_derived)
    SearchExportPage.save_profile(page.pk, result_profile_derived)
    page.refresh_from_db()
    assert page.working_data == {
        result_profile_derived.id: result_profile_derived.to_json()
    }


def test_save_profiles(result_profile_derived, result_profile_derived_another):
    page: SearchExportPage = SearchExportPageFactory()
    SearchExportPage.save_profile(page.pk, result_profile_derived)
    SearchExportPage.save_profile(page.pk, result_profile_derived_another)
    page.refresh_from_db()
    assert page.working_data == {
        result_profile_derived.id: result_profile_derived.to_json(),
        result_profile_derived_another.id: result_profile_derived_another.to_json(),
    }
