from unittest.mock import patch, PropertyMock

import pytest
from celery import group, shared_task

from whoweb.search.models import SearchExport
from whoweb.search.tasks import (
    generate_pages,
    fetch_mx_domains,
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


@shared_task(bind=True, max_retries=1, default_retry_delay=0.01)
def dummy_derive_task(self, i):
    # if i % 4 == 0:
    #     self.retry()
    return i


@shared_task
def dummy_finalize_page_task():
    return True


@shared_task
def dummy_mx_task(i):
    return i


@shared_task
def err_task():
    raise ValueError("error")


@patch("whoweb.search.models.SearchExport.upload_to_static_bucket")
@patch("whoweb.search.models.export.MXDomain.objects")
@patch("whoweb.search.models.SearchExport.PAGE_DELAY", new_callable=PropertyMock)
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
    PAGE_DELAY,
    mx_object_mock,
    static_bucket_mock,
    query_contact_invites_defer_validation,
):
    export: SearchExport = SearchExportFactory(
        query=query_contact_invites_defer_validation, charge=True, notify=True
    )
    export = export._set_target(save=True)
    PAGE_DELAY.return_value = 0
    gen_pages_mock.side_effect = lambda **x: SearchExportPageFactory.create_batch(
        5, export=export, data=None
    )

    get_derivation_tasks_mock.return_value = list(
        dummy_derive_task.si(i) for i in range(0, 2)
    )
    get_mx_task_group_mock.return_value = group(
        fetch_mx_domains.si(range(0, 2)) for i in range(0, 5)
    )

    sigs = export.processing_signatures()
    res = sigs.apply(throw=False)

    assert gen_pages_mock.call_count == 1
    assert get_derivation_tasks_mock.call_count == 5
    assert post_derive_mock.call_count == 5
    assert upload_validation_mock.call_count == 1
    assert get_validation_mock.call_count == 1
    assert do_post_valid_mock.call_count == 1
    assert notify_mock.call_count == 1
    assert static_bucket_mock.call_count == 1
