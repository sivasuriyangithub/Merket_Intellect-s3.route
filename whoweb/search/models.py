from django.db import models

# Create your models here.


class FilteredSearchQuery(models.Model):

    with_invites = models.BooleanField(default=False)

    class Meta:
        abstract = True

    def __str__(self):
        return "%s object (%s)" % (self.__class__.__name__, "embedded")
