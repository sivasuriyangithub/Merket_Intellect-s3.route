import django_filters
import graphene
from django_filters.rest_framework import FilterSet
from graphene import relay
from graphene.types.generic import GenericScalar
from graphene_django import DjangoObjectType, DjangoConnectionField
from graphene_django.filter import DjangoFilterConnectionField, GlobalIDFilter
from rest_framework.permissions import IsAuthenticated

from whoweb.accounting.types import TransactionObjectType
from whoweb.contrib.graphene_django.types import GuardedObjectType
from whoweb.contrib.rest_framework.filters import ObjectPermissionsFilter
from whoweb.contrib.rest_framework.permissions import (
    IsSuperUser,
    ObjectPermissions,
)
from whoweb.payments.permissions import MemberOfBillingAccountPermissionsFilter
from . import models
from .models.profile import PERSONAL, WORK, DerivationCache

DeferChoices = graphene.Enum.from_enum(models.FilteredSearchQuery.DeferOptions)

ContactFilterChoices = graphene.Enum.from_enum(
    models.FilteredSearchQuery.ContactFilterOptions
)

ExportFormatChoices = graphene.Enum.from_enum(models.ExportOptions.FormatOptions,)

GradedEmailTypeChoices = graphene.Enum(
    "GradedEmailTypeOptions", [("PERSONAL", PERSONAL), ("WORK", WORK)]
)


class FilteredSearchFilterElement(DjangoObjectType):
    field = graphene.String()
    truth = graphene.Boolean()
    value = GenericScalar()

    class Meta:
        model = models.FilteredSearchFilterElement


class FilteredSearchFilters(DjangoObjectType):
    limit = graphene.Int()
    skip = graphene.Int()
    required = graphene.List(FilteredSearchFilterElement)
    desired = graphene.List(FilteredSearchFilterElement)
    profiles = graphene.List(graphene.String)

    class Meta:
        model = models.FilteredSearchFilters


class ExportOptions(DjangoObjectType):
    webhooks = graphene.List(graphene.String)
    title = graphene.String()
    metadata = GenericScalar()
    format = graphene.Field(ExportFormatChoices)

    class Meta:
        model = models.ExportOptions


class QuerySource(DjangoObjectType):
    cls = graphene.String()
    object_id = graphene.String()

    class Meta:
        model = models.QuerySource


class FilteredSearchQueryObjectType(DjangoObjectType):
    user_id = graphene.String()
    defer = graphene.List(DeferChoices)
    contact_filters = graphene.List(ContactFilterChoices)
    with_invite = graphene.Boolean()
    export = graphene.Field(ExportOptions)
    filters = graphene.Field(FilteredSearchFilters)
    source = graphene.Field(QuerySource)

    class Meta:
        model = models.FilteredSearchQuery


class SearchExportFilterSet(FilterSet):
    billing_seat = GlobalIDFilter(field_name="billing_seat__public_id")
    billing_account = GlobalIDFilter(field_name="billing_seat__organization__public_id")
    seat = GlobalIDFilter(field_name="billing_seat__seat__public_id")
    network = GlobalIDFilter(field_name="billing_seat__seat__organization__public_id")

    class Meta:
        model = models.SearchExport
        fields = (
            "uuid",
            "billing_seat",
            "billing_account",
            "seat",
            "network",
        )


SearchExportStatusChoices = graphene.Enum.from_enum(
    models.SearchExport.ExportStatusOptions
)


class SearchExportNode(GuardedObjectType):
    class Meta:
        model = models.SearchExport
        interfaces = (relay.Node,)
        filterset_class = SearchExportFilterSet
        permission_classes = [IsSuperUser | IsAuthenticated]
        filter_backends = [
            MemberOfBillingAccountPermissionsFilter | ObjectPermissionsFilter
        ]
        fields = (
            "uuid",
            "billing_seat",
            "query",
            "tags",
            "status",
            "status_changed",
            "sent",
            "sent_at",
            "progress_counter",
            "target",
            "rows_uploaded",
            "notify",
            "charge",
            "on_trial",
            "created",
        )

    query = graphene.Field(FilteredSearchQueryObjectType)
    tags = graphene.List(graphene.String, resolver=lambda x, i: x.tags.all())
    status = graphene.Field(SearchExportStatusChoices)
    charged = graphene.Int(name="charge")
    transactions = graphene.List(TransactionObjectType)
    file_url = graphene.String(description="Link to download as csv file.")
    json_url = graphene.String(description="Link to download as json file.")
    result_url = graphene.String(description="Link to paginated result resource.")

    def resolve_charged(self: models.SearchExport, info):
        return self.charged

    def resolve_transactions(self: models.SearchExport, info):
        return self.transactions

    def resolve_file_url(self: models.SearchExport, info):
        return self.get_absolute_url()

    def resolve_json_url(self: models.SearchExport, info):
        return self.get_absolute_url("json")

    def resolve_result_url(self: models.SearchExport, info):
        return self.get_result_rest_url()


class GradedEmailType(graphene.ObjectType):
    email = graphene.String()
    grade = graphene.String()
    email_type = graphene.Field(GradedEmailTypeChoices)
    is_passing = graphene.Boolean()
    is_personal = graphene.Boolean()
    is_work = graphene.Boolean()
    domain = graphene.String()


class GradedPhoneType(graphene.ObjectType):
    status = graphene.String()
    phone_type = graphene.String()
    number = graphene.String()


class SocialLinkType(graphene.ObjectType):
    url = graphene.String()
    type_id = graphene.String()

    def resolve_type_id(self, info):
        try:
            return self.typeName
        except AttributeError:
            return self.get("typeName")


class HistoryEntry(graphene.Interface):
    id = graphene.ID()
    user_id = graphene.ID()
    start_date = graphene.DateTime()
    end_date = graphene.DateTime()
    city = graphene.String()
    state = graphene.String()
    country = graphene.String()
    is_current = graphene.Boolean()


class EmploymentEntry(graphene.ObjectType):
    company_name = graphene.String()
    title = graphene.String()
    description = graphene.String()

    class Meta:
        interfaces = (HistoryEntry,)


class EducationEntry(graphene.ObjectType):
    school = graphene.String()
    degree = graphene.String()
    major = graphene.String()
    course = graphene.String()
    institution = graphene.String()

    class Meta:
        interfaces = (HistoryEntry,)


class SkillType(graphene.ObjectType):
    tag = graphene.String()


class GenderDiversityType(graphene.ObjectType):
    male = graphene.Float()
    female = graphene.Float()


class EthnicDiversityType(graphene.ObjectType):
    multiple = graphene.Float()
    hispanic = graphene.Float()
    black = graphene.Float()
    asian = graphene.Float()
    white = graphene.Float()
    native = graphene.Float()


class DiversityType(graphene.ObjectType):
    gender = graphene.List(GenderDiversityType)
    ethnic = graphene.List(EthnicDiversityType)


class ResultProfileObjectType(graphene.ObjectType):
    id = graphene.String()
    updated = graphene.DateTime()
    relevance_score = graphene.String()
    first_name = graphene.String()
    last_name = graphene.String()
    company = graphene.String()
    title = graphene.String()
    business_function = graphene.String()
    seniority_level = graphene.String()
    industry = graphene.String()
    picture_url = graphene.String()
    city = graphene.String()
    state = graphene.String()
    country = graphene.String()
    geo_loc = graphene.List(graphene.Float)
    email = graphene.String()
    grade = graphene.String()
    emails = graphene.List(graphene.String)
    graded_emails = graphene.List(GradedEmailType)
    graded_phones = graphene.List(GradedPhoneType)
    social_links = graphene.List(SocialLinkType)
    li_url = graphene.String()
    twitter = graphene.String()
    facebook = graphene.String()
    current_experience = graphene.Field(EmploymentEntry)
    experience = graphene.List(EmploymentEntry)
    education_history = graphene.List(EducationEntry)
    diversity = graphene.Field(DiversityType)
    total_experience = graphene.Int()
    time_at_current_company = graphene.Int()
    time_at_current_position = graphene.Int()
    skills = graphene.List(SkillType)
    attenuated_skills = GenericScalar()

    status = graphene.String(source="derivation_status",)

    def resolve_id(self, info):
        try:
            return self._id
        except AttributeError:
            return self.get("_id")


class IDInFilter(django_filters.BaseCSVFilter, django_filters.CharFilter):
    pass


class DerivationCacheFilter(django_filters.FilterSet):
    billing_seat = GlobalIDFilter(
        field_name="billing_seat__public_id", lookup_expr="exact"
    )
    profile_id = django_filters.CharFilter(field_name="profile_id", lookup_expr="exact")
    profile_id__in = IDInFilter(field_name="profile_id", lookup_expr="in")

    class Meta:
        model = DerivationCache
        fields = ["billing_seat", "profile_id", "profile_id__in"]


class DerivationStoreNode(GuardedObjectType):
    emails = graphene.List(GradedEmailType)
    phones = graphene.List(GradedPhoneType)

    class Meta:
        model = DerivationCache
        interfaces = (relay.Node,)
        filterset_class = DerivationCacheFilter
        permission_classes = [IsSuperUser | IsAuthenticated]
        filter_backends = (MemberOfBillingAccountPermissionsFilter,)
        fields = (
            "billing_seat",
            "profile_id",
            "emails",
            "phones",
        )


class FilterValueListNode(GuardedObjectType):
    tags = graphene.List(graphene.String, resolver=lambda x, i: x.tags.all())

    class Meta:
        model = models.FilterValueList
        filter_fields = []
        interfaces = (relay.Node,)
        permission_classes = [IsSuperUser | ObjectPermissions]
        filter_backends = (ObjectPermissionsFilter,)
        fields = (
            "id",
            "name",
            "description",
            "type",
            "tags",
            "values",
            "billing_seat",
            "created",
            "modified",
        )


class Query(graphene.ObjectType):
    derivations = DjangoFilterConnectionField(DerivationStoreNode)
    search_exports = DjangoFilterConnectionField(SearchExportNode)
    filter_value_lists = DjangoFilterConnectionField(FilterValueListNode)
