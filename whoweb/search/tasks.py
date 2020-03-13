import logging
from math import ceil

from celery import group, shared_task
from celery.exceptions import MaxRetriesExceededError
from django.db.models import F
from requests import HTTPError, Timeout, ConnectionError
from redis.exceptions import ConnectionError as RedisConnectionError

from whoweb.core.router import router
from whoweb.search.events import ALERT_XPERWEB, PAGES_SPAWNED
from whoweb.search.models import SearchExport, ResultProfile
from whoweb.search.models.export import MXDomain, SearchExportPage
from whoweb.search.models.profile import VALIDATED, COMPLETE, FAILED, RETRY, WORK
from kombu.exceptions import OperationalError

logger = logging.getLogger(__name__)

NETWORK_ERRORS = [
    HTTPError,
    Timeout,
    ConnectionError,
    OperationalError,
    RedisConnectionError,
]
MAX_DERIVE_RETRY = 3

MAX_NUM_PAGES_TO_PROCESS_IN_SINGLE_TASK = 5


@shared_task(
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
    return len(pages)


@shared_task(
    bind=True,
    max_retries=3000,
    track_started=True,
    ignore_result=False,
    autoretry_for=NETWORK_ERRORS,
)
def do_process_page(self, page_pk):
    page = SearchExportPage.objects.get(pk=page_pk)
    if page.export.is_done_processing_pages:
        return "Export already done"
    if not page.export.should_derive_email:
        return page.populate_data_directly(task_context=self.request)

    if tasks := page.get_derivation_tasks():
        page.status = SearchExportPage.STATUS.working
        page.pending_count = len(tasks)
        page.save()
        chrd = group(tasks) | finalize_page.si(pk=page.pk).on_error(
            finalize_page.si(pk=page.pk)
        )
        return self.replace(chrd)
    else:
        return "No page tasks required. Page done."


@shared_task(bind=True, ignore_result=False, autoretry_for=NETWORK_ERRORS)
def spawn_do_page_process_tasks(self, prefetch_multiplier, export_id):
    export = SearchExport.objects.get(pk=export_id)
    if export.is_done_processing_pages:
        return "Done"
    num_pages = ceil(export.pages.count() * prefetch_multiplier)
    if empty_pages := export.get_next_empty_page(num_pages):
        empty_page_ids = [page.pk for page in empty_pages]
        tasks = group(
            [
                do_process_page.signature(
                    args=(page_id,),
                    immutable=True,
                    countdown=i * SearchExport.PAGE_DELAY,
                )
                for i, page_id in enumerate(empty_page_ids)
            ]
        )
        export.log_event(PAGES_SPAWNED, data={"signatures": repr(tasks)})
        return self.replace(tasks)
    return "Done with no pages found."


@shared_task(bind=True, ignore_result=False, autoretry_for=NETWORK_ERRORS)
def do_post_pages_completion(self, export_id):
    export = SearchExport.objects.get(pk=export_id)
    return export.do_post_pages_completion(task_context=self.request)


@shared_task(bind=True, autoretry_for=NETWORK_ERRORS)
def validate_rows(self, export_id):
    try:
        export = SearchExport.objects.get(pk=export_id)
    except SearchExport.DoesNotExist:
        return 404
    return export.upload_validation(task_context=self.request)


@shared_task(autoretry_for=NETWORK_ERRORS, bind=True)
def fetch_validation_results(self, export_id):
    try:
        export = SearchExport.objects.get(pk=export_id)
    except SearchExport.DoesNotExist:
        return 404

    complete = export.get_validation_status(task_context=self.request)
    if complete is False:
        raise self.retry(cooldown=60, max_retries=24 * 60)


@shared_task(bind=True, autoretry_for=NETWORK_ERRORS)
def do_post_validation_completion(self, export_id):
    try:
        export = SearchExport.objects.get(pk=export_id)
    except SearchExport.DoesNotExist:
        return 404
    return export.do_post_validation_completion(task_context=self.request)


@shared_task(autoretry_for=NETWORK_ERRORS)
def send_notification(export_id):
    try:
        export = SearchExport.objects.get(pk=export_id)
    except SearchExport.DoesNotExist:
        return 404
    return export.send_link()


@shared_task(ignore_result=False, autoretry_for=NETWORK_ERRORS)
def fetch_mx_domains(domains):
    mxds = MXDomain.objects.filter(domain__in=domains)
    for mxd in mxds:
        try:
            return mxd.fetch_mx()
        except Exception as e:
            logger.exception(e)


@shared_task(bind=True, autoretry_for=NETWORK_ERRORS)
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
        SearchExportPage.objects.filter(pk=page_pk).update(
            pending_count=F("pending_count") - 1
        )
        return False
    else:
        if add_invite_key:
            profile.get_invite_key()
        page = SearchExportPage.save_profile(page_pk, profile)
        return getattr(page, "pk", 404)


@shared_task(
    bind=True,
    max_retries=MAX_DERIVE_RETRY,
    default_retry_delay=90,
    retry_backoff=90,
    ignore_result=False,
    rate_limit="15/m",
    autoretry_for=NETWORK_ERRORS,
)
def process_derivation_slow(
    self, page_pk, profile_data, defer, omit_failures, add_invite_key, filters=None
):
    try:
        return process_derivation(
            self,
            page_pk,
            profile_data,
            defer,
            omit_failures,
            add_invite_key,
            filters=filters,
        )
    except MaxRetriesExceededError:
        try:
            SearchExportPage.objects.filter(pk=page_pk).update(
                pending_count=F("pending_count") - 1
            )
        except:
            pass


@shared_task(
    bind=True,
    max_retries=MAX_DERIVE_RETRY,
    default_retry_delay=90,
    retry_backoff=90,
    ignore_result=False,
    rate_limit="60/m",
    autoretry_for=NETWORK_ERRORS,
)
def process_derivation_fast(
    self, page_pk, profile_data, defer, omit_failures, add_invite_key, filters=None
):
    try:
        return process_derivation(
            self,
            page_pk,
            profile_data,
            defer,
            omit_failures,
            add_invite_key,
            filters=filters,
        )
    except MaxRetriesExceededError:
        try:
            SearchExportPage.objects.filter(pk=page_pk).update(
                pending_count=F("pending_count") - 1
            )
        except:
            pass


@shared_task(
    bind=True, max_retries=250, ignore_result=False, autoretry_for=NETWORK_ERRORS
)
def finalize_page(self, pk):
    export_page = SearchExportPage.objects.get(pk=pk)  # allow DoesNotExist exception
    export_page.do_post_derive_process(task_context=self.request)


@shared_task(
    bind=True, max_retries=250, ignore_result=False, autoretry_for=NETWORK_ERRORS
)
def compress_working_pages(self, export_id, page_ids):
    export = SearchExport.objects.get(pk=export_id)  # allow DoesNotExist exception
    export.compress_working_pages(page_ids=page_ids, task_context=self.request)
