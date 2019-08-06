from django.db import models

# Create your models here.
from whoweb.contrib.postgres.abstract_models import AbstractEmbeddedModel


class FilteredSearchQuery(AbstractEmbeddedModel):

    with_invites = models.BooleanField(default=False)
