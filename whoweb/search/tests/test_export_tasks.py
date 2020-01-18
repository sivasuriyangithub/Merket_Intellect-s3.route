from unittest.mock import patch

import celery
import pytest
from celery import group

from config import celery_app
from whoweb.search.models import SearchExport
from whoweb.search.models.export import SearchExportPage
from whoweb.search.tasks import generate_pages, do_process_page_chunk, fetch_mx_domain
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


@patch("whoweb.search.models.export.SearchExportPage.populate_data_directly")
def test_process_pages_task_no_async_page_tasks(
    populate_data_directly_mock, query_no_contact, settings
):
    settings.CELERY_TASK_ALWAYS_EAGER = True

    export: SearchExport = SearchExportFactory(query=query_no_contact, charge=True)
    SearchExportPageFactory.create_batch(10, export=export, data=None)
    assert do_process_page_chunk.delay(3, export.pk).get() == True
    assert populate_data_directly_mock.call_count == 3


# @patch("celery.result.assert_will_not_block")
@patch("whoweb.search.models.export.SearchExportPage.get_derivation_tasks")
def test_process_pages_task_produces_replacement(
    get_derivation_tasks_mock,
    # no_block_mock,
    query_contact_invites_defer_validation,
    redis,
    mocker,
):
    export: SearchExport = SearchExportFactory(
        query=query_contact_invites_defer_validation, charge=True
    )
    SearchExportPageFactory.create_batch(3, export=export, data=None)
    replacement = mocker.spy(celery.Task, "replace")

    @celery_app.task
    def dummy_derive_task(i):
        return i

    get_derivation_tasks_mock.return_value = [
        dummy_derive_task.si(1),
        dummy_derive_task.si(2),
    ]

    do_process_page_chunk.apply((3, export.pk))
    assert replacement.call_count == 1
    for page in export.pages.all():
        assert page.status == SearchExportPage.STATUS.complete
    assert get_derivation_tasks_mock.call_count == 3


@patch("whoweb.core.router.router.alert_xperweb_export_completion")
@patch("whoweb.search.models.export.MXDomain.objects")
@patch("whoweb.search.models.SearchExport.get_mx_task_group")
@patch("whoweb.search.models.SearchExport.send_link")
@patch("whoweb.search.models.SearchExport.do_post_validation_completion")
@patch("whoweb.search.models.SearchExport.get_validation_status")
@patch("whoweb.search.models.SearchExport.upload_validation")
@patch("whoweb.search.models.export.SearchExportPage.do_post_derive_process")
@patch("whoweb.search.models.export.SearchExportPage.get_derivation_tasks")
@patch("whoweb.search.models.SearchExport.generate_pages")
def test_integration_all_processing_tasks(
    gen_pages_mock,
    get_derivation_tasks_mock,
    post_derive_mock,
    upload_validation_mock,
    get_validation_mock,
    do_post_valid_mock,
    notify_mock,
    get_mx_task_group_mock,
    mx_object_mock,
    alert_xperweb_mock,
    query_contact_invites_defer_validation,
):
    export: SearchExport = SearchExportFactory(
        query=query_contact_invites_defer_validation, charge=True, notify=True
    )
    export = export._set_target(save=True)

    ct = 0

    def page_gen_effect(task_context=None):
        nonlocal ct
        if ct < 2:
            ct = ct + 1
            return SearchExportPageFactory.create_batch(20, export=export, data=None)
        return None

    gen_pages_mock.side_effect = page_gen_effect

    @celery_app.task(bind=True)
    def dummy_derive_task(self, i):
        if i % 4 == 0:
            self.retry()
        return i

    @celery_app.task
    def noop():
        return True

    @celery_app.task
    def dummy_finalize_page_task():
        return True

    get_derivation_tasks_mock.return_value = list(
        dummy_derive_task.si(i).on_error(noop.s()) for i in range(0, 10)
    )

    @celery_app.task
    def dummy_mx_task(i):
        return i

    get_mx_task_group_mock.return_value = group(
        fetch_mx_domain.si(i) for i in range(0, 10)
    )

    sigs = export.processing_signatures()
    res = sigs.apply()
    assert gen_pages_mock.call_count == 3
    assert get_derivation_tasks_mock.call_count == 40
    assert post_derive_mock.call_count == 40
    assert upload_validation_mock.call_count == 1
    assert get_validation_mock.call_count == 1
    assert do_post_valid_mock.call_count == 1
    assert notify_mock.call_count == 1
    assert alert_xperweb_mock.call_count == 1
    assert res.get() == True
