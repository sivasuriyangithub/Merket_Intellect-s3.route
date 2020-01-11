from datetime import datetime, timedelta

from celery import chain
from django.conf import settings
from django.db import models
from django.forms import model_to_dict

from whoweb.search.models import FilteredSearchQuery, SearchExport
from whoweb.contrib.postgres.fields import EmbeddedModelField
from .reply import ReplyTo
from .base import ColdemailBaseModel
from ..api import resource as api
from ..api.resource import ListRecord
from ..events import UPLOAD_CAMPAIGN_LIST_URL, UPLOAD_CAMPAIGN_MESSAGE
from .campaign_message import CampaignMessage


class SingleColdEmail(ColdemailBaseModel):

    EVENT_REVERSE_NAME = "single_coldemail"

    api_class = api.SingleEmail

    message = models.ForeignKey(CampaignMessage, on_delete=models.SET_NULL, null=True)
    email = models.EmailField()
    from_name = models.CharField(max_length=255)
    send_date = models.DateTimeField()
    test = models.BooleanField(default=False)
    use_credits_method = models.CharField(max_length=90)

    views = models.PositiveIntegerField()
    clicks = models.PositiveIntegerField()
    optouts = models.PositiveIntegerField()

    def publish(self):
        from ..tasks import publish_single_email

        if self.is_published:
            return

        message_sigs = self.message.publish(apply_tasks=False)
        chain(message_sigs, publish_single_email.si(self.pk)).apply_async()

    def api_upload(self, is_sync=False):
        if self.is_published:
            return

        fromaddress, self.from_name = ReplyTo.get_or_create(self)

        create_args = dict(
            email=self.email,
            subject=("[TEST] " + self.message.subject).encode("utf-8")
            if self.test
            else self.message.subject.encode("utf-8"),
            messageid=self.message.coldemail_id,
            date=self.send_date or None,
            whoisid=settings.COLD_EMAIL_WHOIS,
            profileid=settings.COLD_EMAIL_SINGLE_EMAIL_PROFILEID,
            fromaddress=fromaddress,
            fromname=self.from_name,
        )
        if is_sync:
            cold_single_email = self.api_create(is_sync=True, **create_args)
        else:
            cold_single_email = yield self.api_create(**create_args)
        self.coldemail_id = cold_single_email.id
        self.status = self.STATUS.published
        self.save()
        self.save_as_inbox_message()

    def save_as_inbox_message(self):
        inbox = Inbox.find(email=self.email)
        inbox.messages.create(id=ObjectId(), campaign_message=self.message, source=self)
        inbox.save()
