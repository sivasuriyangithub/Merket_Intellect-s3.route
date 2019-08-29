import logging

from celery.result import GroupResult
from requests import HTTPError, Timeout, ConnectionError

from config import celery_app
from whoweb.search.models import SearchExport, ResultProfile
from whoweb.search.models.export import MXDomain, SearchExportPage
from whoweb.search.models.profile import VALIDATED, COMPLETE, FAILED, RETRY

logger = logging.getLogger(__name__)

NETWORK_ERRORS = [HTTPError, Timeout, ConnectionError]


@celery_app.task(
    bind=True, max_retries=3000, track_started=True, autoretry_for=NETWORK_ERRORS
)
def process_export(self, export_id):
    logger.info("Processing <SearchExport %s>", export_id)
    try:
        export = SearchExport.objects.get(export_id)
    except SearchExport.DoesNotExist:
        return

    if export.is_done_processing_pages:
        export.do_post_pages_completion(task_context=self.request)
        return True

    next_page = export.get_next_empty_page()
    if next_page:
        done = next_page.do_page_process(task_context=self.request)
        if done:
            raise self.retry(max_retries=2000, countdown=3)
    else:
        try:
            pages = export.generate_pages(task_context=self.request)
        except (HTTPError, Timeout, ConnectionError) as exc:
            raise self.retry(exc=exc, max_retries=2000, retry_backoff=True)
        if pages:
            raise self.retry(max_retries=2000, countdown=4)
        else:
            export.do_post_page_completion(task_context=self.request)


@celery_app.task(
    bind=True, max_retries=3000, ignore_result=False, autoretry_for=NETWORK_ERRORS
)
def check_export_has_data(self, export_id):
    """
    Useful in a chain to trigger another task after the export is finished.
    """
    try:
        export = SearchExport.objects.get(export_id)
    except SearchExport.DoesNotExist:
        return

    if export.is_done_processing_pages:
        return True
    else:
        self.retry(countdown=600)


@celery_app.task(bind=True, autoretry_for=NETWORK_ERRORS)
def validate_rows(self, export_id):
    try:
        export = SearchExport.objects.get(export_id)
    except SearchExport.DoesNotExist:
        return
    return export.upload_validation(task_context=self.request)


@celery_app.task(autoretry_for=NETWORK_ERRORS, bind=True)
def fetch_validation_results(self, export_id):
    try:
        export = SearchExport.objects.get(export_id)
    except SearchExport.DoesNotExist:
        return

    complete = export.get_validation_status(task_context=self.request)
    if complete is False:
        raise self.retry(cooldown=60, max_retries=24 * 60)


@celery_app.task(autoretry_for=NETWORK_ERRORS)
def send_notification(export_id):
    try:
        export = SearchExport.objects.get(export_id)
    except SearchExport.DoesNotExist:
        return
    return export.send_link()


@celery_app.task(autoretry_for=NETWORK_ERRORS)
def refund_against_target(export_id):
    try:
        export = SearchExport.objects.get(export_id)
    except SearchExport.DoesNotExist:
        return
    return export.refund_against_target()


@celery_app.task(ignore_result=False, autoretry_for=NETWORK_ERRORS)
def fetch_mx_domain(domain):
    try:
        mxd = MXDomain.objects.get(domain=domain)
    except MXDomain.DoesNotExist:
        return
    return mxd.fetch_mx()


@celery_app.task(autoretry_for=NETWORK_ERRORS)
def spawn_mx_group(export_id):
    try:
        export = SearchExport.objects.get(export_id)
    except SearchExport.DoesNotExist:
        return
    group_result = export.get_mx_task_group()
    if group_result is None:
        return False
    return group_result.id


@celery_app.task(
    bind=True, max_retries=90, ignore_result=False, autoretry_for=NETWORK_ERRORS
)
def header_check(self, group_result_id):
    """
    Chords are buggy; this is the chord header check as a standalone task.
    If using this task's signature in a chain, you probably want it mutable: `.s()`
    """

    if not group_result_id:
        return True

    results = GroupResult.restore(group_result_id)
    if any(not result.ready() for result in results) and self.request.retries < 80:
        raise self.retry(countdown=300)


def process_derivation(
    task, page_pk, profile_data, defer, omit_failures, add_invite_key, filters
):
    """
    :type task: celery.Task
    :type page_pk: basestring
    :type profile: xperweb.search.models.ResultProfile
    :type defer: list
    :type omit_failures: boolean
    :rtype: boolean
    """
    profile = ResultProfile.from_json(profile_data)
    status = profile.derivation_status
    if not status in [VALIDATED, COMPLETE]:
        status = profile.derive_contact(defer, filters)

    if status == RETRY:
        raise task.retry()
    elif status == FAILED and omit_failures:
        return False
    else:
        if add_invite_key:
            profile.get_invite_key()
        return SearchExportPage.save_profile(page_pk, profile)


@celery_app.task(
    bind=True,
    max_retries=5,
    default_retry_delay=90,
    retry_backoff=60,
    ignore_result=False,
    rate_limit="10/m",
    autoretry_for=NETWORK_ERRORS,
)
def process_derivation_slow(
    self, page_pk, profile_data, defer, omit_failures, add_invite_key, filters=None
):
    return process_derivation(
        self,
        page_pk,
        profile_data,
        defer,
        omit_failures,
        add_invite_key,
        filters=filters,
    )


@celery_app.task(
    bind=True,
    max_retries=5,
    default_retry_delay=60,
    retry_backoff=60,
    ignore_result=False,
    rate_limit="40/m",
    autoretry_for=NETWORK_ERRORS,
)
def process_derivation_fast(
    self, page_pk, profile_data, defer, omit_failures, add_invite_key, filters=None
):
    return process_derivation(
        self,
        page_pk,
        profile_data,
        defer,
        omit_failures,
        add_invite_key,
        filters=filters,
    )


@celery_app.task(
    bind=True, max_retries=250, ignore_result=False, autoretry_for=NETWORK_ERRORS
)
def finalize_page(self, pk, group_result_id):
    # Chords are buggy; this is the chord header check:
    results = GroupResult.restore(group_result_id)
    if any(not result.ready() for result in results) and self.request.retries < 240:
        raise self.retry(countdown=30)

    export_page = SearchExportPage.objects.get(pk)  # allow DoesNotExist exception
    export_page.do_post_page_process(task_context=self.request)
    process_export.delay(export_page.export.pk)
