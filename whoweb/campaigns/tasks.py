from datetime import timedelta

from celery import shared_task
from django.db import transaction
from requests import HTTPError, Timeout

from whoweb.campaigns.models import IntervalCampaignRunner
from whoweb.campaigns.models.base import BaseCampaignRunner, DripTooSoonError
from whoweb.coldemail.models import ColdCampaign

NETWORK_ERRORS = [HTTPError, Timeout, ConnectionError]


@shared_task(autoretry_for=NETWORK_ERRORS)
def set_published(pk, run_id=None):
    runner = BaseCampaignRunner.available_objects.get(pk=pk)
    if str(run_id) != str(runner.run_id):
        return
    runner.status = runner.CampaignRunnerStatusOptions.PUBLISHED
    runner.save()


@shared_task(bind=True, autoretry_for=NETWORK_ERRORS)
def publish_next_interval(self, pk, run_id=None):
    runner = IntervalCampaignRunner.available_objects.get(pk=pk)
    if str(run_id) != str(runner.run_id):
        return
    if runner.status == runner.CampaignRunnerStatusOptions.PAUSED:
        return
    runner.publish(task_context=self.request)


@shared_task(bind=True, autoretry_for=NETWORK_ERRORS)
def publish_drip(self, pk, root_pk, following_pk, run_id=None, *args, **kwargs):
    with transaction.atomic():
        runner = BaseCampaignRunner.available_objects.select_for_update().get(pk=pk)
        if str(run_id) != str(runner.run_id):
            return
        if runner.status == runner.CampaignRunnerStatusOptions.PAUSED:
            return
        root_campaign = ColdCampaign.objects.get(pk=root_pk)
        following = ColdCampaign.objects.get(pk=following_pk)
        try:
            runner.publish_drip(
                root_campaign=root_campaign,
                following=following,
                task_context=self.request,
                *args,
                **kwargs,
            )
        except DripTooSoonError as e:
            raise self.retry(countdown=e.countdown)


@shared_task(autoretry_for=NETWORK_ERRORS)
def ensure_stats(pk):
    runner = BaseCampaignRunner.available_objects.get(pk=pk)
    runner.fetch_statistics()


# @shared_task(autoretry_for=NETWORK_ERRORS)
# def save_all_inbox_messages(list_id, source_id, message_id):
#     OnboardingCampaign.save_all_inbox_messages(
#         campaign_list=CampaignList.objects.with_id(list_id),
#         source=ReplyCampaign.objects.with_id(source_id),
#         message_id=message_id,
#     )


@shared_task(autoretry_for=NETWORK_ERRORS)
def catch_missed_drips():
    for runner in (
        BaseCampaignRunner.available_objects.filter(
            status=BaseCampaignRunner.CampaignRunnerStatusOptions.PUBLISHED
        )
        .exclude(messages=None)
        .exclude(campaigns=None)
    ):
        for campaign in runner.campaigns.all():
            if drip_tasks := runner.resume_drip_tasks(
                root_campaign=campaign, noop_after=timedelta(weeks=2)
            ):
                drip_tasks.apply_async()


@shared_task(autoretry_for=NETWORK_ERRORS)
def on_complete_generate_icebreakers(
    pk, rule_index, campaign_id=None, export_id=None, *args, **kwargs
):
    runner = BaseCampaignRunner.available_objects.get(pk=pk)
    runner.generate_icebreakers(
        rule_index, campaign_id=campaign_id, export_id=export_id,
    )
