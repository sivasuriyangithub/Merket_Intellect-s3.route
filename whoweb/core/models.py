from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import JSONField
from django.db import models

from model_utils.models import TimeStampedModel, TimeFramedModel


class ModelEvent(TimeStampedModel, TimeFramedModel):
    message = models.TextField()
    code = models.IntegerField(blank=True, null=True)
    data = JSONField(blank=True, null=True)

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True)
    object_id = models.PositiveIntegerField(null=True)
    ref = GenericForeignKey()

    class Meta:
        verbose_name = "event"
