from enum import Enum

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

    class FormatOptions(str, Enum):
        NESTED = "nested"
        FLAT = "flat"

    webhooks = ArrayField(models.URLField(), default=list, blank=True)
    title = models.CharField(max_length=255, blank=True, default="")
    metadata = JSONField(blank=True, default=dict)
    format = models.CharField(
        default=FormatOptions.NESTED,
        max_length=255,
        blank=True,
        choices=[(o.value, o.name) for o in FormatOptions],
    )

    def is_flat(self):
        return self.format == self.FormatOptions.FLAT


class QuerySource(AbstractEmbeddedModel):
    class Meta:
        managed = False

    cls = models.CharField(max_length=255, blank=True, default="")
    object_id = models.CharField(max_length=255, blank=True, default="")


def default_contact_filters():
    return [
        FilteredSearchQuery.ContactFilterOptions.WORK,
        FilteredSearchQuery.ContactFilterOptions.PERSONAL,
        FilteredSearchQuery.ContactFilterOptions.SOCIAL,
        FilteredSearchQuery.ContactFilterOptions.PROFILE,
    ]


class PublicDeferOptions(str, Enum):
    CONTACT = "CONTACT"
    COMPANY_COUNTS = "COMPANY_COUNTS"
    DEGREE_LEVELS = "DEGREE_LEVELS"
    VALIDATION = "VALIDATION"
    PHONE_VALIDATION = "PHONE_VALIDATION"
    ALPHA = "NYMERIA"
    BETA = "ROCKETREACH"
    GAMMA = "TOOFR"
    DELTA = "ANYMAIL"
    EPSILON = "PDL"
    ZETA = "FULLCONTACT"
    ETA = "PIPL"
    THETA = "HUNTER"
    IOTA = "NORBERT"
    KAPPA = "NAME2DOMAIN"
    LAMBDA = "CLEARBIT"
    MU = "GCSE"


class FilteredSearchQuery(AbstractEmbeddedModel):
    class Meta:
        managed = False

    class DeferOptions(str, Enum):
        CONTACT = "contact"
        COMPANY_COUNTS = "company_counts"
        DEGREE_LEVELS = "degree_levels"
        VALIDATION = "validation"
        PHONE_VALIDATION = "phone_validation"
        ALPHA = "nymeria"
        BETA = "rocketreach"
        GAMMA = "toofr"
        DELTA = "anymail"
        EPSILON = "pdl"
        ZETA = "fullcontact"
        ETA = "pipl"
        THETA = "hunter"
        IOTA = "norbert"
        KAPPA = "name2domain"
        LAMBDA = "clearbit"
        MU = "gcse"

    class ContactFilterOptions(str, Enum):
        WORK = "work"
        PERSONAL = "personal"
        SOCIAL = "social"
        PHONE = "phone"
        PROFILE = "profile"

    user_id = models.CharField(max_length=36, null=True, blank=True)
    filters = EmbeddedModelField(FilteredSearchFilters, default=FilteredSearchFilters)
    defer = ArrayField(
        base_field=models.CharField(
            max_length=50, choices=[(o.value, o.name) for o in DeferOptions]
        ),
        default=list,
        blank=True,
    )
    with_invites = models.BooleanField(default=False)
    contact_filters = ArrayField(
        base_field=models.CharField(
            max_length=50, choices=[(o.value, o.name) for o in ContactFilterOptions]
        ),
        default=default_contact_filters,
        blank=True,
    )
    export = EmbeddedModelField(ExportOptions, default=ExportOptions)
    source = EmbeddedModelField(QuerySource, null=True, blank=True, default=QuerySource)

    def __eq__(self, other):
        if hasattr(other, "serialize"):
            return self.serialize() == other.serialize()
        return self.serialize() == other
