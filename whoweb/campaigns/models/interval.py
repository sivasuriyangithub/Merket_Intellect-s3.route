from django.db import models

from whoweb.coldemail.models import CampaignList
from .base import (
    AbstractBaseCampaignRunner,
    AbstractBaseSendingRule,
    AbstractBaseDripRecord,
)
from .metaclass import Messages, Drips


class IntervalSendingRule(AbstractBaseSendingRule):
    manager = models.ForeignKey("IntervalCampaignRunner", on_delete=models.CASCADE)


class IntervalDripRecord(AbstractBaseDripRecord):
    manager = models.ForeignKey("IntervalCampaignRunner", on_delete=models.CASCADE)


class IntervalCampaignBase(AbstractBaseCampaignRunner):
    class Meta:
        abstract = True

    interval_hours = models.PositiveIntegerField(
        default=24, help_text="Interval between each campaign."
    )
    max_sends = models.PositiveIntegerField(
        null=True, help_text="Total campaigns allowed for this manager."
    )

    def create_cold_campaign(self, *args, **kwargs):
        if self.max_sends and len(self.campaigns) >= self.max_sends:
            self.modify(status=CampaignStatus.COMPLETE, modified=datetime.utcnow())
            return
        return super().create_cold_campaign(*args, **kwargs)

    def create_campaign_list(self, *args, **kwargs):
        campaign_list = super().create_campaign_list(*args, **kwargs)
        self.query.filters.skip += self.budget
        self.query.save()
        return campaign_list


class IntervalCampaignRunner(IntervalCampaignBase):
    """
    This style of campaign is will send the same message to the entire query, up to budget.
    """

    messages = Messages(IntervalSendingRule)
    drips = Drips(IntervalDripRecord)

    use_credits_method = models.CharField(max_length=63, blank=True, null=True)
    open_credit_budget = models.IntegerField()
    preset_campaign_list = models.ForeignKey(
        CampaignList, on_delete=models.CASCADE, null=True
    )

    def publish(self, apply_tasks=True, task_context=None, *args, **kwargs):
        from xperweb.campaign.tasks import publish_next_interval

        sigs, campaign = super().publish(
            apply_tasks=False, task_context=task_context, *args, **kwargs
        )
        if not campaign:
            return None, None
        later = datetime.utcnow() + timedelta(hours=self.interval_hours)
        publish_next_sig = publish_next_interval.signature(
            args=(self.pk,), kwargs={"run_id": self.run_id}, immutable=True, eta=later
        )
        self.log_event(
            CAMPAIGN_SIGNATURES, task=task_context, data={"sigs": repr(sigs)}
        )
        if apply_tasks:
            return (sigs.apply_async(), publish_next_sig.apply_async()), campaign
        else:
            return (sigs, publish_next_sig), campaign
