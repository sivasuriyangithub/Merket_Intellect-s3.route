from unittest.mock import patch

import pytest
from celery import group

from whoweb.search.models import SearchExport
from whoweb.search.models.export import SearchExportPage
from whoweb.search.tasks import (
    generate_pages,
    process_pages,
    do_process_page_chunk,
    check_do_more_pages,
)
from whoweb.search.tests.factories import SearchExportFactory, SearchExportPageFactory

pytestmark = pytest.mark.django_db


@patch("whoweb.search.models.SearchExport.generate_pages")
def test_generate_pages_task(
    pages_mock, query_contact_invites_defer_validation, settings
):
    settings.CELERY_TASK_ALWAYS_EAGER = True

    export: SearchExport = SearchExportFactory(
        query=query_contact_invites_defer_validation, charge=True
    )
    pages_mock.side_effect = lambda *x, **y: SearchExportPageFactory.create_batch(
        8, export=export, data=None
    )
    assert generate_pages.si(export.pk).apply_async().get() == 8
    assert pages_mock.call_count == 1


def test_process_pages_task_no_pages(query_contact_invites_defer_validation, settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True

    export: SearchExport = SearchExportFactory(
        query=query_contact_invites_defer_validation, charge=True
    )
    assert (
        do_process_page_chunk.delay(5, export.pk).get() == "No empty pages remaining."
    )


def test_process_pages_task_pages_done(
    query_contact_invites_defer_validation, settings
):
    settings.CELERY_TASK_ALWAYS_EAGER = True

    export: SearchExport = SearchExportFactory(
        query=query_contact_invites_defer_validation, charge=True
    )
    SearchExportPageFactory.create_batch(3, export=export)
    assert (
        do_process_page_chunk.delay(5, export.pk).get() == "No empty pages remaining."
    )


@patch("whoweb.search.models.export.SearchExportPage.do_page_process")
def test_process_pages_task_no_async_page_tasks(
    page_process_mock, query_no_contact, settings
):
    settings.CELERY_TASK_ALWAYS_EAGER = True

    export: SearchExport = SearchExportFactory(query=query_no_contact, charge=True)
    SearchExportPageFactory.create_batch(3, export=export, data=None)
    page_process_mock.return_value = []
    assert (
        do_process_page_chunk.delay(3, export.pk).get()
        == "No page tasks required. Pages done."
    )
    assert page_process_mock.call_count == 3


@patch("whoweb.search.models.export.SearchExportPage.do_page_process")
@patch("celery.Task.replace")
def test_process_pages_task_produces_replacement(
    replace_mock, page_process_mock, query_contact_invites_defer_validation, settings
):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    export: SearchExport = SearchExportFactory(
        query=query_contact_invites_defer_validation, charge=True
    )
    SearchExportPageFactory.create_batch(3, export=export, data=None)
    do_process_page_chunk.delay(3, export.pk)
    assert page_process_mock.call_count == 3
    for page in export.pages.all():
        assert page.status == SearchExportPage.STATUS.working
    assert replace_mock.call_count == 1


@patch("whoweb.search.models.export.SearchExportPage.do_page_process")
@patch("whoweb.search.models.SearchExport.generate_pages")
@patch("whoweb.search.models.scroll.ScrollSearch.get_profiles_for_page")
def test_integration_generate_pages_and_process_pages_tasks(
    get_profiles_mock,
    gen_pages_mock,
    page_process_mock,
    query_contact_invites_defer_validation,
    search_result_profiles,
    celery_app,
    settings,
):
    settings.CELERY_TASK_ALWAYS_EAGER = True

    export: SearchExport = SearchExportFactory(
        query=query_contact_invites_defer_validation, charge=True
    )
    get_profiles_mock.return_value = search_result_profiles
    export.ensure_search_interface()

    @celery_app.task
    def dummy_derive_task(i):
        return i

    @celery_app.task
    def dummy_finalize_page_task():
        return True

    page_process_mock.return_value = group(
        dummy_derive_task.si(i) for i in range(0, 10)
    ) | dummy_finalize_page_task.si().on_error(dummy_finalize_page_task.si())

    ct = 0

    def page_gen_effect(task_context=None):
        nonlocal ct
        if ct < 2:
            ct = ct + 1
            return SearchExportPageFactory.create_batch(20, export=export, data=None)
        return None

    gen_pages_mock.side_effect = page_gen_effect
    sigs = generate_pages.si(export.pk) | check_do_more_pages.s(export.pk)
    res = sigs.apply_async(throw=True, disable_sync_subtasks=False)
    assert gen_pages_mock.call_count == 3
    assert page_process_mock.call_count == 40
    assert res.get() == "Done"
