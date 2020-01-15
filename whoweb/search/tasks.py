import logging

from celery import group
from requests import HTTPError, Timeout, ConnectionError
from sentry_sdk import capture_exception

from config import celery_app
from whoweb.core.router import router
from whoweb.search.models import SearchExport, ResultProfile
from whoweb.search.models.export import MXDomain, SearchExportPage
from whoweb.search.models.profile import VALIDATED, COMPLETE, FAILED, RETRY, WORK

logger = logging.getLogger(__name__)

NETWORK_ERRORS = [HTTPError, Timeout, ConnectionError]
MAX_DERIVE_RETRY = 3


@celery_app.task(
    bind=True, max_retries=3000, track_started=True, autoretry_for=NETWORK_ERRORS
)
def alert_xperweb(self, export_id):
    logger.info("Letting Xperweb know <SearchExport %s> is done", export_id)
    try:
        export = SearchExport.objects.get(pk=export_id)
    except SearchExport.DoesNotExist:
        return 404
    router.alert_xperweb_export_completion(
        idempotency_key=export.uuid, amount=export.charged
    )
    export.status = export.STATUS.complete
    export.save()


@celery_app.task(
    bind=True,
    max_retries=3000,
    track_started=True,
    ignore_result=False,
    autoretry_for=NETWORK_ERRORS,
)
def process_export(self, export_id):
    logger.info("Processing <SearchExport %s>", export_id)
    try:
        export = SearchExport.objects.get(pk=export_id)
    except SearchExport.DoesNotExist:
        return 404

    if export.is_done_processing_pages:
        export.do_post_pages_completion(task_context=self.request)
        return "Exited having done page processing."

    page_tasks = []
    empty_pages = export.get_next_empty_page(3)
    for page in empty_pages:
        page_sigs = page.do_page_process(task_context=self.request)
        if page_sigs:
            page_tasks.append((page_sigs, page))
    if page_tasks:
        tasks = [pt[0] for pt in page_tasks]
        pages = [pt[1] for pt in page_tasks]
        for page in pages:
            page.status = SearchExportPage.STATUS.working
            page.save()
        raise self.replace(
            (
                group(*tasks)
                | process_export.si(export.pk).on_error(process_export.si(export.pk))
            )
        )
    else:
        try:
            pages = export.generate_pages(task_context=self.request)
        except (HTTPError, Timeout, ConnectionError) as exc:
            raise self.retry(exc=exc, max_retries=2000, retry_backoff=True)
        if pages:
            raise self.retry(max_retries=2000, countdown=4)
        else:
            export.do_post_pages_completion(task_context=self.request)
            return "Exited after no additional pages generated."


@celery_app.task(
    bind=True, max_retries=5000, ignore_result=False, autoretry_for=NETWORK_ERRORS
)
def check_export_has_data(self, export_id):
    """
    Useful in a chain to trigger another task after the export is finished.
    """
    try:
        export = SearchExport.objects.get(pk=export_id)
    except SearchExport.DoesNotExist:
        return 404

    if export.is_done_processing_pages:
        return True
    else:
        self.retry(countdown=600)


@celery_app.task(bind=True, autoretry_for=NETWORK_ERRORS)
def validate_rows(self, export_id):
    try:
        export = SearchExport.objects.get(pk=export_id)
    except SearchExport.DoesNotExist:
        return 404
    return export.upload_validation(task_context=self.request)


@celery_app.task(autoretry_for=NETWORK_ERRORS, bind=True)
def fetch_validation_results(self, export_id):
    try:
        export = SearchExport.objects.get(pk=export_id)
    except SearchExport.DoesNotExist:
        return 404

    complete = export.get_validation_status(task_context=self.request)
    if complete is False:
        raise self.retry(cooldown=60, max_retries=24 * 60)


@celery_app.task(autoretry_for=NETWORK_ERRORS)
def send_notification(export_id):
    try:
        export = SearchExport.objects.get(pk=export_id)
    except SearchExport.DoesNotExist:
        return 404
    return export.send_link()


@celery_app.task(autoretry_for=NETWORK_ERRORS)
def do_post_validation_completion(export_id):
    try:
        export = SearchExport.objects.get(pk=export_id)
    except SearchExport.DoesNotExist:
        return 404
    return export.do_post_validation_completion()


@celery_app.task(ignore_result=False, autoretry_for=NETWORK_ERRORS)
def fetch_mx_domain(domain):
    try:
        mxd = MXDomain.objects.get(domain=domain)
    except MXDomain.DoesNotExist:
        return 404
    try:
        return mxd.fetch_mx()
    except:
        capture_exception()
        return None


@celery_app.task(bind=True, autoretry_for=NETWORK_ERRORS)
def spawn_mx_group(self, export_id):
    try:
        export = SearchExport.objects.get(pk=export_id)
    except SearchExport.DoesNotExist:
        return 404
    group_signature = export.get_mx_task_group()
    if group_signature is None:
        return False
    raise self.replace(group_signature)


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
        deferred = list(set(defer))  # copy, unique
        if task.request.retries < MAX_DERIVE_RETRY:
            # don't call toofr unless absolutely necessary, like on final attempt
            deferred.append("toofr")
        elif WORK in filters and "toofr" not in defer:
            # if we want work emails and aren't explicitly preventing toofr data,
            # call validation in real time
            deferred = [d for d in defer if d != "validation"]
        status = profile.derive_contact(deferred, filters, producer=page_pk)

    if status == RETRY:
        raise task.retry()
    elif status == FAILED and omit_failures:
        return False
    else:
        if add_invite_key:
            profile.get_invite_key()
        page = SearchExportPage.save_profile(page_pk, profile)
        return getattr(page, "pk", 404)


@celery_app.task(
    bind=True,
    max_retries=MAX_DERIVE_RETRY,
    default_retry_delay=90,
    retry_backoff=90,
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
    max_retries=MAX_DERIVE_RETRY,
    default_retry_delay=90,
    retry_backoff=90,
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
def finalize_page(self, pk):
    export_page = SearchExportPage.objects.get(pk=pk)  # allow DoesNotExist exception
    export_page.do_post_page_process(task_context=self.request)
