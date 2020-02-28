from typing import Union

import tagulous
from django.db import models
from django.utils.translation import ugettext_lazy as _
from model_utils import Choices
from model_utils.fields import MonitorField
from model_utils.models import TimeStampedModel, SoftDeletableModel
from tagulous.models import TagField, TagModel

from whoweb.coldemail.api.resource import (
    CreateableResource,
    ListableResource,
    UpdateableResource,
    DeleteableResource,
)
from whoweb.contrib.fields import ObscureIdMixin
from whoweb.core.models import EventLoggingModel
from whoweb.users.models import Seat


class ColdEmailTagModel(TagModel):
    class TagMeta:
        force_lowercase = True


class ColdemailBaseModel(
    ObscureIdMixin, TimeStampedModel, EventLoggingModel, SoftDeletableModel
):
    api_class: Union[
        CreateableResource, ListableResource, UpdateableResource, DeleteableResource
    ] = None

    STATUS = Choices(
        (0, "created", "Created"),
        (2, "pending", "Pending"),
        (4, "published", "Published"),
        (8, "paused", "Paused"),
    )
    seat = models.ForeignKey(Seat, on_delete=models.CASCADE, null=True, blank=True)

    status = models.IntegerField(
        _("status"), db_index=True, choices=STATUS, blank=True, default=STATUS.created
    )
    status_changed = MonitorField(_("status changed"), monitor="status")
    coldemail_id = models.CharField(max_length=100)
    is_removed_changed = MonitorField("deleted at", monitor="is_removed")
    published_at = MonitorField(
        monitor="status", when=[STATUS.published], null=True, default=None, blank=True
    )
    tags = TagField(to=ColdEmailTagModel, blank=True)

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.__class__.__name__} {self.pk}" + (
            f"(Published {self.published_at})"
            if self.status == self.STATUS.published
            else ""
        )

    @classmethod
    def api_create(cls, **kwargs):
        return cls.api_class.create(**kwargs)

    def api_retrieve(self):
        if not self.coldemail_id:
            return
        res = self.api_class.retrieve(id=self.coldemail_id)
        if not res:
            self.coldemail_id = None
            self.save()
        return res

    @property
    def is_locked(self):
        return self.status in [self.STATUS.pending, self.STATUS.published]

    @property
    def is_published(self):
        return bool(self.coldemail_id) or self.status == self.STATUS.published
