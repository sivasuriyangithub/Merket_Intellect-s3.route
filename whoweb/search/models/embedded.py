import logging

from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import ArrayField, JSONField
from django.db import models
from model_utils import Choices

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

    FORMAT_CHOICES = Choices(("nested", "NESTED", "nested"), ("flat", "FLAT", "flat"))
    webhooks = ArrayField(models.URLField(), default=list, blank=True)
    title = models.CharField(max_length=255, blank=True, default="")
    metadata = JSONField(blank=True, default=dict)
    format = models.CharField(
        default=FORMAT_CHOICES.NESTED,
        max_length=255,
        blank=True,
        choices=FORMAT_CHOICES,
    )

    def is_flat(self):
        return self.format == "flat"


def default_contact_filters():
    return [
        FilteredSearchQuery.CONTACT_FILTER_CHOICES.WORK,
        FilteredSearchQuery.CONTACT_FILTER_CHOICES.PERSONAL,
        FilteredSearchQuery.CONTACT_FILTER_CHOICES.SOCIAL,
        FilteredSearchQuery.CONTACT_FILTER_CHOICES.PROFILE,
    ]


class FilteredSearchQuery(AbstractEmbeddedModel):
    class Meta:
        managed = False

    PUBLIC_DEFER_CHOICES = Choices(
        ("contact", "CONTACT", "Contact"),
        ("company_counts", "COMPANY_COUNTS", "Company Counts"),
        ("degree_levels", "DEGREE_LEVELS", "Degree Levels"),
        ("validation", "VALIDATION", "Validation"),
        ("phone_validation", "PHONE_VALIDATION", "Phone Validation"),
    )  # for html serializer
    DEFER_CHOICES = Choices(
        ("contact", "CONTACT", "Contact"),
        ("company_counts", "COMPANY_COUNTS", "Company Counts"),
        ("degree_levels", "DEGREE_LEVELS", "Degree Levels"),
        ("validation", "VALIDATION", "Validation"),
        ("phone_validation", "PHONE_VALIDATION", "Phone Validation"),
        ("nymeria", "NYMERIA", "Nymeria Service"),
        ("rocketreach", "ROCKETREACH", "Rocketreach Service"),
        ("toofr", "TOOFR", "Toofr (Find Emails) Service"),
        ("anymail", "ANYMAIL", "Anymail Service"),
        ("talentiq", "TALENTIQ", "TalentIQ Service"),
        ("fullcontact", "FULLCONTACT", "Fullcontact Service"),
        ("pipl", "PIPL", "Pipl Service"),
        ("hunter", "HUNTER", "Hunter (pattern) Service"),
        ("norbert", "NORBERT", "norbert Service"),
        ("name2domain", "NAME2DOMAIN", "name2domain Service"),
        ("clearbit", "CLEARBIT", "Clearbit Service"),
        ("gcse", "GCSE", "Google Custom Search Service"),
    )
    CONTACT_FILTER_CHOICES = Choices(
        ("work", "WORK", "Work"),
        ("personal", "PERSONAL", "Personal"),
        ("social", "SOCIAL", "Social"),
        ("phone", "PHONE", "Phone"),
        ("profile", "PROFILE", "Profile"),
    )
    user_id = models.CharField(max_length=36, null=True, blank=True)
    filters = EmbeddedModelField(FilteredSearchFilters, default=FilteredSearchFilters)
    defer = ArrayField(
        base_field=models.CharField(max_length=50, choices=DEFER_CHOICES),
        default=list,
        blank=True,
    )
    with_invites = models.BooleanField(default=False)
    contact_filters = ArrayField(
        base_field=models.CharField(max_length=50, choices=CONTACT_FILTER_CHOICES),
        default=default_contact_filters,
        blank=True,
    )
    export = EmbeddedModelField(ExportOptions, default=ExportOptions)
