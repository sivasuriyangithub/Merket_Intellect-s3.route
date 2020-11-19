import django_filters
import graphene
from django_filters.rest_framework import FilterSet
from graphene import relay
from graphene.types.generic import GenericScalar
from graphene_django import DjangoConnectionField
from graphene_django.filter import DjangoFilterConnectionField, GlobalIDFilter

from whoweb.payments.permissions import MemberOfBillingAccountPermissionsFilter
from whoweb.campaigns import models
from whoweb.coldemail import models as coldemail_models
from whoweb.contrib.graphene_django.types import GuardedObjectType
from whoweb.contrib.rest_framework.permissions import IsSuperUser, ObjectPermissions
from whoweb.search.schema import FilteredSearchQueryObjectType

CampaignRunnerStatusChoices = graphene.Enum(
    "CampaignRunnerStatusChoices",
    models.BaseCampaignRunner.STATUS._identifier_map.items(),
)


class TagsFilter(django_filters.BaseInFilter, django_filters.CharFilter):
    pass


class CampaignRunnerFilter(FilterSet):
    status = django_filters.TypedChoiceFilter(
        choices=[(c[1], c[0]) for c in models.BaseCampaignRunner.STATUS._triples],
        coerce=lambda x: getattr(models.BaseCampaignRunner.STATUS, x),
    )
    published = django_filters.DateRangeFilter(field_name="published",)
    published_after = django_filters.DateFilter(
        field_name="published", lookup_expr="gt"
    )
    published_before = django_filters.DateFilter(
        field_name="published", lookup_expr="lt"
    )
    tags = TagsFilter(field_name="tags__name")
    id = GlobalIDFilter(field_name="public_id", lookup_expr="exact")

    class Meta:
        model = models.BaseCampaignRunner
        fields = (
            "status",
            "published",
            "billing_seat",
            "id",
        )


class Message(GuardedObjectType):
    class Meta:
        model = coldemail_models.CampaignMessage


class MessageTemplate(GuardedObjectType):
    tags = graphene.List(graphene.String, resolver=lambda x, i: x.tags.all())

    class Meta:
        model = coldemail_models.CampaignMessageTemplate


class ProfileLogEntry(graphene.ObjectType):
    email = graphene.String()
    web_id = graphene.String(name="profile_id")


class Campaign(GuardedObjectType):
    click_log = graphene.List(ProfileLogEntry, name="clickProfiles")
    open_log = graphene.List(ProfileLogEntry, name="openProfiles")
    reply_log = graphene.List(ProfileLogEntry, name="replyProfiles")
    good_log = graphene.List(ProfileLogEntry, name="goodProfiles")
    sent_profiles = graphene.List(graphene.String)

    class Meta:
        interfaces = (relay.Node,)
        model = coldemail_models.ColdCampaign
        fields = ("click_log", "open_log", "reply_log", "good_log", "sent_profiles")

    def resolve_sent_profiles(self, info):
        return (profile.id for profile in self.campaign_list.export.get_profiles())


class SendingRule(GuardedObjectType):
    class Meta:
        model = models.SendingRule


class DripRecord(GuardedObjectType):
    class Meta:
        model = models.DripRecord


class TrackingParam(graphene.ObjectType):
    param = graphene.String()
    value = graphene.String()


class SimpleCampaignRunnerNode(GuardedObjectType):
    query = graphene.Field(FilteredSearchQueryObjectType)
    sending_rules = graphene.List(SendingRule)
    drips = graphene.List(DripRecord, source="drip_records")
    campaigns = DjangoConnectionField(Campaign)
    tags = graphene.List(graphene.String, resolver=lambda x, i: x.tags.all())
    transactions = GenericScalar()
    tracking_params = graphene.List(TrackingParam)
    status = graphene.Field(CampaignRunnerStatusChoices)

    class Meta:
        model = models.SimpleDripCampaignRunner
        interfaces = (relay.Node,)
        filterset_class = CampaignRunnerFilter
        permission_classes = [IsSuperUser | ObjectPermissions]
        filter_backends = (MemberOfBillingAccountPermissionsFilter,)
        fields = (
            "budget",
            "query",
            "campaigns",
            "sending_rules",
            "modified",
            "billing_seat",
            "tags",
            "drips",
            "transactions",
            "tracking_params",
            "use_credits_method",
            "open_credit_budget",
            "from_name",
            "status",
            "status_changed",
            "published",
            "title",
            "created",
        )


class IntervalCampaignRunnerNode(GuardedObjectType):
    query = graphene.Field(FilteredSearchQueryObjectType)
    sending_rules = graphene.List(SendingRule)
    drips = graphene.List(DripRecord, source="drip_records")
    campaigns = DjangoConnectionField(Campaign)
    tags = graphene.List(graphene.String, resolver=lambda x, i: x.tags.all())
    transactions = GenericScalar()
    tracking_params = graphene.List(TrackingParam)
    status = graphene.Field(CampaignRunnerStatusChoices)

    class Meta:
        model = models.IntervalCampaignRunner
        interfaces = (relay.Node,)
        filterset_class = CampaignRunnerFilter

        permission_classes = [IsSuperUser | ObjectPermissions]
        filter_backends = (MemberOfBillingAccountPermissionsFilter,)

        fields = (
            "query",
            "billing_seat",
            "budget",
            "title",
            "tags",
            "sending_rules",
            "drips",
            "campaigns",
            "transactions",
            "tracking_params",
            "interval_hours",
            "max_sends",
            "from_name",
            "status",
            "status_changed",
            "published",
            "created",
            "modified",
        )


class Query(graphene.ObjectType):
    simple_campaigns = DjangoFilterConnectionField(SimpleCampaignRunnerNode)
    interval_campaigns = DjangoFilterConnectionField(IntervalCampaignRunnerNode)
