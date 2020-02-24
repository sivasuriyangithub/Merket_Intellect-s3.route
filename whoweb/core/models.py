import tagulous
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import JSONField
from django.db import models

from model_utils.models import TimeStampedModel, TimeFramedModel
from six import string_types


class ModelEvent(TimeStampedModel, TimeFramedModel):
    message = models.TextField()
    code = models.IntegerField(blank=True, null=True)
    data = JSONField(blank=True, null=True)

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True)
    object_id = models.PositiveIntegerField(null=True)
    ref = GenericForeignKey()

    class Meta:
        verbose_name = "event"


DEFAULT_REVERSE_NAME = "EVENT_REVERSE_NAME"


class EventsField(GenericRelation):
    """
    A GenericRelation that looks for a ``EVENT_REVERSE_NAME`` class-attribute and
    automatically uses that `related_query_name`.

    """

    def prepare_class(self, sender, **kwargs):
        if not sender._meta.abstract:
            assert hasattr(sender, DEFAULT_REVERSE_NAME), (
                "To use EventsField, the model '%s' must have a %s choices class attribute."
                % (sender.__name__, DEFAULT_REVERSE_NAME)
            )
            self.related_query_name = getattr(sender, DEFAULT_REVERSE_NAME)


class EventLoggingModel(models.Model):
    events = EventsField(ModelEvent)

    class Meta:
        abstract = True

    def log_event(self, evt, *, start=None, end=None, task=None, **data):
        if hasattr(task, "id"):
            data["task_id"] = task.id
        if isinstance(evt, string_types):
            code = 0
            message = evt
        else:
            code = evt[0]
            message = evt[1]
        try:
            ModelEvent.objects.create(
                ref=self, code=code, message=message, start=start, end=end, data=data
            )
        except TypeError:
            ModelEvent.objects.create(
                ref=self,
                code=code,
                message=message,
                start=start,
                end=end,
                data=str(data),
            )
