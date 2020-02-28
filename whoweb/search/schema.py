import graphene
from graphene import relay
from graphene.types.generic import GenericScalar
from graphene_django.filter import DjangoFilterConnectionField
from rest_framework_guardian.filters import ObjectPermissionsFilter

from whoweb.contrib.graphene_django.types import GuardedObjectType
from whoweb.contrib.rest_framework.permissions import (
    IsSuperUser,
    ObjectPermissions,
)
from .models import SearchExport, FilteredSearchQuery, ExportOptions

DeferChoices = graphene.Enum(
    "DeferChoices", FilteredSearchQuery.PUBLIC_DEFER_CHOICES._identifier_map.items()
)

ContactFilterChoices = graphene.Enum(
    "ContactFilterChoices",
    FilteredSearchQuery.CONTACT_FILTER_CHOICES._identifier_map.items(),
)

ExportFormatChoices = graphene.Enum(
    "ExportFormatChoices", ExportOptions.FORMAT_CHOICES._identifier_map.items(),
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
            "seat",
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


class Query(graphene.ObjectType):
    search_exports = DjangoFilterConnectionField(SearchExportNode)
