from datetime import datetime, timedelta

from django.db import models
from django.forms import model_to_dict

from whoweb.search.models import FilteredSearchQuery, SearchExport
from whoweb.contrib.postgres.fields import EmbeddedModelField
from .base import ColdemailBaseModel
from ..api import resource as api
from ..api.resource import ListRecord
from ..events import UPLOAD_CAMPAIGN_LIST_URL, UPLOAD_CAMPAIGN_MESSAGE


class CampaignMessage(ColdemailBaseModel):

    EVENT_REVERSE_NAME = "campaign_message"

    api_class = api.Message

    title = models.CharField(max_length=255)
    subject = models.TextField()
    plain_content = models.TextField()
    html_content = models.TextField()
    editor = models.CharField(max_length=255)

    def publish(self, apply_tasks=True):
        from ..tasks import publish_message

        if self.is_published:
            return

        self.status = self.STATUS.pending

        sig = publish_message.si(self.pk)
        if apply_tasks:
            sig.apply_async()
        else:
            return sig

    def api_upload(self, is_sync=False, task_context=None):
        self.log_event(UPLOAD_CAMPAIGN_MESSAGE, task=task_context)
        if self.coldemail_id:
            return
        cold_msg = self.api_create(
            title=self.title,
            body=(self.html_content or "").encode("utf-8"),
            text=(self.plain_content or "").encode("utf-8"),
            subject=(self.subject or "").encode("utf-8"),
        )
        self.coldemail_id = cold_msg.id
        self.status = self.STATUS.published
        self.save()


class CampaignMessageTemplate(CampaignMessage):
    def publish(self, *args, **kwargs):
        raise NotImplemented

    def api_upload(self, *args, **kwargs):
        raise NotImplemented
