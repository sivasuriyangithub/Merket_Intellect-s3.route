from django.db import models
from rest_framework.reverse import reverse

from whoweb.coldemail.models import CampaignList
from .base import BaseCampaignRunner


class SimpleDripCampaignRunner(BaseCampaignRunner):
    """
    This style of campaign is will send the same message to the entire query, up to budget.
    """

    use_credits_method = models.CharField(max_length=63, blank=True, null=True)
    open_credit_budget = models.IntegerField(blank=True, null=True)

    def create_cold_campaign(self, *args, **kwargs):
        if (
            self.campaigns.exists()
        ):  # We only create one. That's what makes it...simple.
            return
        return super().create_cold_campaign(*args, **kwargs)

    def get_absolute_url(self):
        return reverse(
            "simpledripcampaignrunner-detail", kwargs={"public_id": self.public_id}
        )
