import logging
from math import ceil

from celery import group, chain, chord
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

MAX_NUM_PAGES_TO_PROCESS_IN_SINGLE_TASK = 5


@celery_app.task(
    bind=True,
    max_retries=2000,
    retry_backoff=True,
    track_started=True,
    ignore_result=False,
    autoretry_for=NETWORK_ERRORS,
)
def generate_pages(self, export_id):
    export = SearchExport.objects.get(pk=export_id)
    pages = export.generate_pages(task_context=self.request)
    return len(pages) if pages else 0


@celery_app.task(
    bind=True,
    max_retries=3000,
    track_started=True,
    ignore_result=False,
    autoretry_for=NETWORK_ERRORS,
)
def process_pages(self, num_pages, export_id):
    if not num_pages:
        return True
    batch_size = MAX_NUM_PAGES_TO_PROCESS_IN_SINGLE_TASK
    return self.replace(
        chain(
            *[
                do_process_page_chunk.si(batch_size, export_id)
                for _ in range(ceil(num_pages / batch_size))
            ]
        )
    )


@celery_app.task(
    bind=True,
    max_retries=3000,
    track_started=True,
    ignore_result=False,
    autoretry_for=NETWORK_ERRORS,
)
def do_process_page_chunk(self, batch_size, export_id):
    export = SearchExport.objects.get(pk=export_id)
    empty_pages = export.get_next_empty_page(batch_size)
    if not empty_pages:
        return "No empty pages remaining."
    page_chords = []
    for empty_page in empty_pages:
        page_sigs = empty_page.do_page_process(task_context=self.request)
        if not page_sigs:
            continue
        page_chords.append(page_sigs)
        empty_page.status = SearchExportPage.STATUS.working
        empty_page.save()
    if page_chords:
        return self.replace(group(page_chords))
    return "No page tasks required. Pages done."


@celery_app.task(bind=True, ignore_result=False, autoretry_for=NETWORK_ERRORS)
def check_do_more_pages(self, num_pages, export_id):
    if num_pages:
        self.replace(
            chain(
                process_pages.si(num_pages, export_id),
                generate_pages.si(export_id),
                check_do_more_pages.s(export_id),
            )
        )
    return "Done"


@celery_app.task(bind=True, ignore_result=False, autoretry_for=NETWORK_ERRORS)
def do_post_pages_completion(self, export_id):
    export = SearchExport.objects.get(pk=export_id)
    # assert export.is_done_processing_pages, f"{export} not done processing pages."
    export.do_post_pages_completion(task_context=self.request)


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
def do_post_validation_completion(export_id):
    try:
        export = SearchExport.objects.get(pk=export_id)
    except SearchExport.DoesNotExist:
        return 404
    return export.do_post_validation_completion()


@celery_app.task(autoretry_for=NETWORK_ERRORS)
def send_notification(export_id):
    try:
        export = SearchExport.objects.get(pk=export_id)
    except SearchExport.DoesNotExist:
        return 404
    return export.send_link()


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
    export = SearchExport.objects.get(pk=export_id)
    group_signature = export.get_mx_task_group()
    if group_signature is None:
        return False
    return self.replace(group_signature)


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
