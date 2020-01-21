from datetime import timedelta

from celery import shared_task
from django.db.models import Q
from django.utils.timezone import now
from requests import HTTPError, Timeout

from .events import POLL_FOR_LIST_UPLOAD
from .models import ColdCampaign, CampaignList, CampaignMessage, SingleColdEmail

NETWORK_ERRORS = [HTTPError, Timeout, ConnectionError]


@shared_task(bind=True, autoretry_for=NETWORK_ERRORS)
def publish_single_email(self, single_id):
    single_email: SingleColdEmail = SingleColdEmail.objects.select_for_update().get(
        pk=single_id
    )
    if single_email.message.is_published:
        single_email.api_upload(task_context=self.request)


@shared_task(bind=True, autoretry_for=NETWORK_ERRORS)
def publish_message(self, message_id):
    msg: CampaignMessage = CampaignMessage.objects.select_for_update().get(
        pk=message_id
    )
    msg.api_upload(task_context=self.request)


@shared_task(bind=True, autoretry_for=NETWORK_ERRORS)
def upload_list(self, list_id):
    list_record: CampaignList = CampaignList.objects.select_for_update().get(pk=list_id)
    list_record.api_upload(task_context=self.request)


@shared_task(bind=True, ignore_result=False, autoretry_for=NETWORK_ERRORS)
def check_for_list_publication(self, list_id):
    list_record: CampaignList = CampaignList.objects.get(pk=list_id)
    list_record.log_event(POLL_FOR_LIST_UPLOAD, task=self.request)
    cold_list = list_record.api_retrieve()
    if not cold_list:
        return False  # not published
    if int(cold_list.total or 0) == 0:
        raise self.retry(
            retry_backoff=90, max_retries=40, retry_backoff_max=60 * 60 * 4
        )

    campaigns: [ColdCampaign] = ColdCampaign.objects.filter(
        campaign_list=list_id, status=ColdCampaign.STATUS.pending
    ).select_for_update()
    for campaign in campaigns:
        campaign.api_upload(task_context=self.request)


@shared_task(bind=True, autoretry_for=NETWORK_ERRORS)
def try_refund(self, pk, should_orphan=False, orphan_kwargs=None):
    if should_orphan is True:
        orphan = try_refund.s(pk)
        if orphan_kwargs:
            orphan = orphan.set(**orphan_kwargs)
        return orphan.apply_async()
    campaign = ColdCampaign.objects.get(pk=pk)
    if not campaign:
        return
    refund = campaign.try_issue_refund()
    if refund is None:
        raise self.retry(coutdown=60 * 60)
    return refund


@shared_task(autoretry_for=NETWORK_ERRORS)
def update_validation(pk, should_orphan=False):
    if should_orphan is True:
        return update_validation.delay(pk, should_orphan=False)
    campaign = ColdCampaign.objects.get(pk=pk)
    if campaign:
        return campaign.update_validation()


@shared_task(autoretry_for=NETWORK_ERRORS)
def spawn_fetch_campaign_stats():
    late = ColdCampaign.objects.filter(
        Q(published__gte=now() - timedelta(days=14))
        & (Q(stats_fetched__lte=now() - timedelta(hours=4)) | Q(stats=None))
    ).only("pk")
    for campaign in late:
        fetch_campaign_stats.delay(campaign.pk)


@shared_task(rate_limit="30/m", autoretry_for=NETWORK_ERRORS)
def fetch_campaign_stats(campaign_id):
    campaign = ColdCampaign.objects.get(pk=campaign_id)
    if not campaign:
        return
    if campaign.stats_fetched and campaign.stats_fetched >= now() - timedelta(hours=2):
        return
    campaign.fetch_stats()
