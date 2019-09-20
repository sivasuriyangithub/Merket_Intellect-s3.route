import types
from unittest.mock import patch

import pytest

from whoweb.search.models import SearchExport, ResultProfile
from whoweb.search.models.export import SearchExportPage
from whoweb.search.tests.factories import SearchExportFactory, SearchExportPageFactory

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
@patch("whoweb.search.models.ScrollSearch.get_page")
@patch("whoweb.search.models.ScrollSearch.population")
def test_generate_pages(pop_mock, get_page, query_contact_invites, population, pages):
    pop_mock.return_value = population
    export: SearchExport = SearchExportFactory(query=query_contact_invites)
    export._set_target()
    export._generate_pages()
    assert get_page.call_count == pages
    assert export.pages.count() == pages


@pytest.mark.parametrize("population,pages", [(100, 1), (500, 2), (601, 3)])
@patch("whoweb.search.models.ScrollSearch.get_page")
@patch("whoweb.search.models.ScrollSearch.population")
def test_generate_pages_continuation(
    pop_mock, get_page, query_contact_invites, population, pages
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
    assert export.status == "2"


def test_get_next_empty_page():
    export: SearchExport = SearchExportFactory()
    pages: [SearchExportPage] = SearchExportPageFactory.create_batch(
        3, export=export, data=None
    )
    assert export.get_next_empty_page() == pages[0]
    SearchExportPage.objects.filter(pk=pages[0].pk).update(data={"done": True})
    assert export.get_next_empty_page() == pages[1]


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
