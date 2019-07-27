import six
from django.contrib.postgres.fields import JSONField
from django.db import models
from django.utils import timezone
from model_utils import Choices
from model_utils.fields import MonitorField
from model_utils.models import TimeStampedModel, StatusModel, SoftDeletableModel


class ColdEmailObjectProcessingEvent(TimeStampedModel):
    message = models.CharField(max_length=120)
    code = models.IntegerField()
    timestamp = models.DateTimeField(default=timezone.now)
    task_id = models.CharField(max_length=120)
    data = JSONField()


class ColdemailBaseModel(TimeStampedModel, StatusModel, SoftDeletableModel):
    api_class = None
    STATUS = Choices("pending", "published", "paused")

    coldemail_id = models.CharField(max_length=100)
    is_removed_changed = MonitorField("deleted at", monitor="is_removed")
    published_at = MonitorField(monitor="status", when=["published"])
    events = models.ManyToManyField(ColdEmailObjectProcessingEvent)

    class Meta:
        abstract = True

    def __str__(self):
        return (
            f"status: {self.status}" + f", published at {self.published_at}"
            if self.status == self.STATUS.published
            else ""
        )

    @classmethod
    def api_create(cls, **kwargs):
        return cls.api_class.create(**kwargs)

    def api_retrieve(self,):
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

    def log_event(self, message, timestamp=None, task=None, **kwargs):
        if isinstance(message, six.string_types):
            message = (0, message)
        if task is not None:
            kwargs["task_id"] = task.id
        kwargs.setdefault("data", {}).update(
            ref={"cls": self.__class__.__name__, "id": self.pk}
        )
        entry = ColdEmailObjectProcessingEvent.objects.create(
            code=message[0], message=message[1], timestamp=timestamp, **kwargs
        )
        self.events.add(entry)
        return entry
