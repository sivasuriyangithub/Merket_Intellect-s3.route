import re

import bson as bson
from django.conf import settings
from django.db import models
from django.urls import reverse
from model_utils.models import TimeStampedModel

from whoweb.coldemail.api.resource import RoutesObject


class ReplyTo(TimeStampedModel):
    id = models.CharField(primary_key=True, max_length=100, default=bson.ObjectId)
    # campaign = models.ForeignKey("ColdCampaign", on_delete=models.SET_NULL, null=True)
    # single_email = models.ForeignKey(
    #     "ColdSingleEmail", on_delete=models.SET_NULL, null=True
    # )
    mailgun_route_id = models.CharField(max_length=50, null=True)
    coldemail_route_id = models.CharField(
        max_length=50, null=True, help_text="ID of reply route in ColdEmail Router."
    )
    from_name = models.CharField(max_length=255, default="")

    def __str__(self):
        return f"{self.pk} ({self.from_name} in {self.campaign or self.single_email})"

    @classmethod
    def create(cls, campaign=None, single_email=None):
        sender = (campaign or single_email).owner
        from_name = sender.get_from_name() or settings.FROM_NAME
        reply = cls.objects.create(
            campaign=campaign, single_email=single_email, from_name=from_name
        )
        forwarding_webhook = reply.get_reply_webhook()
        route = RoutesObject.create_reply_route(
            match=reply.pk,
            forwarding_address=sender.email,
            forwarding_webhook=forwarding_webhook,
        )
        route_id = route.get("id")
        if not route_id:
            reply.delete()
            return None

        reply.coldemail_route_id = str(route_id)
        reply.save()
        return reply

        # do something with the book

    @property
    def from_address(self):
        return self.from_name.replace(" ", "") + str(self.pk)

    def get_reply_webhook(self):
        return reverse(
            "coldemail:reply_forwarding_webhook", kwargs=dict(match_id=self.pk)
        )

    def log_reply(self, email):
        email = re.search("[^@<\s]+@[^@\s>]+", email).group(0)
        if self.campaign:
            self.campaign.log_reply(email=email)
        elif self.single_email:
            self.single_email.log_reply(email=email)
