from django.contrib.postgres.fields import ArrayField
from django.db import models
from model_utils.models import TimeStampedModel
from tagulous.models import TagField

from whoweb.payments.models import BillingAccountMember
from whoweb.coldemail.models import ColdEmailTagModel


class FilterValueList(TimeStampedModel):
    name = models.CharField(max_length=255)
    description = models.TextField(default="", blank=True)
    type = models.CharField(max_length=255, default="", blank=True)
    tags = TagField(to=ColdEmailTagModel)
    values = ArrayField(models.CharField(max_length=255))
    billing_seat = models.ForeignKey(
        BillingAccountMember, on_delete=models.CASCADE
    )
