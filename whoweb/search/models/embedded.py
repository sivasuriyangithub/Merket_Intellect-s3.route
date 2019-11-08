import logging

from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import ArrayField, JSONField
from django.db import models

from whoweb.contrib.postgres.abstract_models import AbstractEmbeddedModel
from whoweb.contrib.postgres.fields import EmbeddedModelField, EmbeddedArrayField

logger = logging.getLogger(__name__)
User = get_user_model()


class FilteredSearchFilterElement(AbstractEmbeddedModel):
    class Meta:
        managed = False

    field = models.CharField(max_length=255)
    value = JSONField()
    truth = models.BooleanField(default=True)


class FilteredSearchFilters(AbstractEmbeddedModel):
    class Meta:
        managed = False

    limit = models.IntegerField(null=True)
    skip = models.IntegerField(null=True, default=0)
    required = EmbeddedArrayField(
        EmbeddedModelField(
            FilteredSearchFilterElement, default=FilteredSearchFilterElement
        ),
        default=list,
    )
    desired = EmbeddedArrayField(
        EmbeddedModelField(
            FilteredSearchFilterElement, default=FilteredSearchFilterElement
        ),
        default=list,
    )
    profiles = ArrayField(models.CharField(max_length=300), default=list, blank=True)


class ExportOptions(AbstractEmbeddedModel):
    class Meta:
        managed = False

    webhooks = ArrayField(models.URLField(), default=list, blank=True)
    format = models.CharField(default="nested", max_length=255, blank=True)

    def is_flat(self):
        return self.format == "flat"


class FilteredSearchQuery(AbstractEmbeddedModel):
    class Meta:
        managed = False

    DEFER_CONTACT = "contact"
    DEFER_COMPANY_Q = "company_counts"
    DEFER_DEGREE_LVL = "degree_levels"
    DEFER_VALIDATION = "validation"
    WORK = "work"
    PERSONAL = "personal"
    SOCIAL = "social"
    PHONE = "phone"
    PROFILE = "profile"

    user_id = models.CharField(max_length=36, null=True, blank=True)
    filters = EmbeddedModelField(FilteredSearchFilters, default=FilteredSearchFilters)
    defer = ArrayField(
        base_field=models.CharField(
            max_length=50,
            choices=(
                (DEFER_CONTACT, DEFER_CONTACT),
                (DEFER_COMPANY_Q, DEFER_COMPANY_Q),
                (DEFER_DEGREE_LVL, DEFER_DEGREE_LVL),
            ),
        ),
        default=list,
        blank=True,
    )
    with_invites = models.BooleanField(default=False)
    contact_filters = ArrayField(
        base_field=models.CharField(
            max_length=50,
            choices=(
                (WORK, WORK),
                (PERSONAL, PERSONAL),
                (SOCIAL, SOCIAL),
                (PHONE, PHONE),
                (PROFILE, PROFILE),
            ),
        ),
        default=list,
        blank=True,
    )
    export = EmbeddedModelField(ExportOptions, default=ExportOptions)
