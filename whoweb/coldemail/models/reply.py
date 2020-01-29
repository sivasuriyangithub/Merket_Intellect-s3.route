import re
from typing import Union

import bson as bson
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models, transaction
from django.urls import reverse
from model_utils.models import TimeStampedModel

from whoweb.coldemail.api.error import ColdEmailError
from whoweb.core.router import external_link
from whoweb.coldemail.api.resource import RoutesObject


class ReplyTo(TimeStampedModel):
    id = models.CharField(primary_key=True, max_length=100, default=bson.ObjectId)
    from_name = models.CharField(max_length=255, default="")

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    replyable_object = GenericForeignKey()

    coldemail_route_id = models.CharField(
        max_length=50, null=True, help_text="ID of reply route in ColdEmail Router."
    )

    def __str__(self):
        return f"{self.pk} ({self.from_name} in {self.replyable_object})"

    @transaction.atomic
    @classmethod
    def get_or_create_with_api(cls, replyable_object):
        instance, created = cls.objects.get_or_create(
            replyable_object=replyable_object, coldemail_route_id__isnull=True,
        )
        if created:
            instance = instance.publish()
        return instance, created

    def publish(self):
        assert hasattr(self.replyable_object, "log_reply")
        sender = self.replyable_object.owner
        route = RoutesObject.create_reply_route(
            match=self.pk,
            forwarding_address=sender.email,
            forwarding_webhook=self.get_reply_webhook(),
        )
        if route_id := route.get("id"):
            from_name = sender.get_from_name() or settings.FROM_NAME
            self.from_name = from_name
            self.coldemail_route_id = str(route_id)
            self.save()
            return self
        else:
            self.delete()
            raise ColdEmailError(message="Route not created.")

    @property
    def from_address(self):
        return self.from_name.replace(" ", "") + str(self.pk)

    def get_reply_webhook(self):
        return external_link(
            reverse("coldemail:reply_forwarding_webhook", kwargs=dict(match_id=self.pk))
        )

    def log_reply(self, email):
        email = re.search("[^@<\s]+@[^@\s>]+", email).group(0)
        if self.replyable_object:
            self.replyable_object.log_reply(email=email)
