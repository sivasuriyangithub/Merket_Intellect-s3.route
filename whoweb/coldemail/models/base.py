from enum import Enum, IntEnum
from typing import Union

from django.db import models
from django.utils.translation import ugettext_lazy as _
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
from whoweb.payments.models import BillingAccountMember
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

    class CampaignObjectStatusOptions(IntEnum):
        CREATED = 0
        PENDING = 2
        PUBLISHED = 4
        PAUSED = 8

    seat = models.ForeignKey(Seat, on_delete=models.CASCADE, null=True, blank=True)
    billing_seat = models.ForeignKey(
        BillingAccountMember, on_delete=models.CASCADE, null=True
    )

    status = models.IntegerField(
        _("status"),
        db_index=True,
        choices=[(s.value, s.name) for s in CampaignObjectStatusOptions],
        blank=True,
        default=CampaignObjectStatusOptions.CREATED,
    )
    status_changed = MonitorField(_("status changed"), monitor="status")
    coldemail_id = models.CharField(max_length=100)
    is_removed_changed = MonitorField(
        "deleted at", monitor="is_removed", editable=False
    )
    published = MonitorField(
        monitor="status",
        when=[CampaignObjectStatusOptions.PUBLISHED],
        null=True,
        default=None,
        blank=True,
    )
    tags = TagField(to=ColdEmailTagModel, blank=True)

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.__class__.__name__} {self.pk}" + (
            f"(Published {self.published})"
            if self.status == self.CampaignObjectStatusOptions.PUBLISHED
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
        return self.status in [
            self.CampaignObjectStatusOptions.PENDING,
            self.CampaignObjectStatusOptions.PUBLISHED,
        ]

    @property
    def is_published(self):
        return (
            bool(self.coldemail_id)
            or self.status == self.CampaignObjectStatusOptions.PUBLISHED
        )
