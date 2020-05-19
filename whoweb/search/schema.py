import graphene
from graphene import relay
from graphene.types.generic import GenericScalar
from graphene_django.filter import DjangoFilterConnectionField
from whoweb.contrib.rest_framework.filters import ObjectPermissionsFilter

from whoweb.contrib.graphene_django.types import GuardedObjectType
from whoweb.contrib.rest_framework.permissions import (
    IsSuperUser,
    ObjectPermissions,
)
from .models import (
    SearchExport,
    FilteredSearchQuery,
    ExportOptions as ExportOptionsModel,
)
from .models.profile import PERSONAL, WORK

DeferChoices = graphene.Enum(
    "DeferChoices", FilteredSearchQuery.PUBLIC_DEFER_CHOICES._identifier_map.items()
)

ContactFilterChoices = graphene.Enum(
    "ContactFilterChoices",
    FilteredSearchQuery.CONTACT_FILTER_CHOICES._identifier_map.items(),
)

ExportFormatChoices = graphene.Enum(
    "ExportFormatChoices", ExportOptionsModel.FORMAT_CHOICES._identifier_map.items(),
)

GradedEmailTypeChoices = graphene.Enum(
    "GradedEmailTypeChoices", [("PERSONAL", PERSONAL), ("WORK", WORK)]
)


class FilteredSearchFilterElement(graphene.ObjectType):
    field = graphene.String()
    truth = graphene.Boolean()
    value = GenericScalar()


class FilteredSearchFilters(graphene.ObjectType):
    limit = graphene.Int()
    skip = graphene.Int()
    required = graphene.List(FilteredSearchFilterElement)
    desired = graphene.List(FilteredSearchFilterElement)
    profiles = graphene.List(graphene.String)


class ExportOptions(graphene.ObjectType):
    webhooks = graphene.List(graphene.String)
    title = graphene.String()
    metadata = GenericScalar()
    format = graphene.Field(ExportFormatChoices)


class FilteredSearchQuery(graphene.ObjectType):
    user_id = graphene.String()
    defer = graphene.List(DeferChoices)
    contact_filters = graphene.List(ContactFilterChoices)
    with_invite = graphene.Boolean()
    export = graphene.Field(ExportOptions)
    filters = graphene.Field(FilteredSearchFilters)


class SearchExportNode(GuardedObjectType):
    query = graphene.Field(FilteredSearchQuery)

    class Meta:
        model = SearchExport
        interfaces = (relay.Node,)
        filter_fields = []
        permission_classes = [IsSuperUser | ObjectPermissions]
        filter_backends = (ObjectPermissionsFilter,)
        fields = (
            "uuid",
            "billing_seat",
            "query",
            "status",
            "status_changed",
            "sent",
            "sent_at",
            "progress_counter",
            "target",
            "notify",
            "charge",
            "on_trial",
        )

    charged = graphene.Int(name="charge")
    file_url = graphene.String(description="Link to download as csv file.")
    json_url = graphene.String(description="Link to download as json file.")

    def resolve_status(self: SearchExport, info):
        return self.get_status_display()

    def resolve_charged(self: SearchExport, info):
        return self.charged

    def resolve_transactions(self: SearchExport, info):
        return self.transactions

    def resolve_file_url(self: SearchExport, info):
        return self.get_absolute_url()

    def resolve_json_url(self: SearchExport, info):
        return self.get_absolute_url("json")


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
    type_id = graphene.String(source="typeId")


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
    id = graphene.String(source="_id",)
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


class Query(graphene.ObjectType):
    search_exports = DjangoFilterConnectionField(SearchExportNode)
