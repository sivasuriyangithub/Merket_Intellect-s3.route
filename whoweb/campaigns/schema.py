import graphene
from graphene import relay
from graphene.types.generic import GenericScalar
from graphene_django.filter import DjangoFilterConnectionField

from whoweb.campaigns import models
from whoweb.coldemail import models as coldemail_models
from whoweb.contrib.graphene_django.types import GuardedObjectType
from whoweb.contrib.rest_framework.permissions import IsSuperUser, ObjectPermissions
from whoweb.search.schema import FilteredSearchQueryObjectType
from whoweb.contrib.rest_framework.filters import ObjectPermissionsFilter


class Message(GuardedObjectType):
    class Meta:
        model = coldemail_models.CampaignMessage


class MessageTemplate(GuardedObjectType):
    tags = graphene.List(graphene.String)

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

    class Meta:
        model = coldemail_models.ColdCampaign


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
    drips = graphene.List(DripRecord)
    campaigns = graphene.List(Campaign)
    get_status_display = graphene.String(name="status_name")
    tags = graphene.List(graphene.String)
    transactions = GenericScalar()
    tracking_params = graphene.List(TrackingParam)

    class Meta:
        model = models.SimpleDripCampaignRunner
        interfaces = (relay.Node,)
        filter_fields = [
            "billing_seat",
        ]
        permission_classes = [IsSuperUser | ObjectPermissions]
        filter_backends = (ObjectPermissionsFilter,)
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
            "get_status_display",
            "status_changed",
            "published",
            "title",
            "status",
        )


class IntervalCampaignRunnerNode(GuardedObjectType):
    query = graphene.Field(FilteredSearchQueryObjectType)
    sending_rules = graphene.List(SendingRule)
    drips = graphene.List(DripRecord)
    campaigns = graphene.List(Campaign)
    get_status_display = graphene.String(name="status_name")
    tags = graphene.List(graphene.String)
    transactions = GenericScalar()
    tracking_params = graphene.List(TrackingParam)

    class Meta:
        model = models.IntervalCampaignRunner
        interfaces = (relay.Node,)
        filter_fields = [
            "billing_seat",
        ]
        permission_classes = [IsSuperUser | ObjectPermissions]
        filter_backends = (ObjectPermissionsFilter,)
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
            "get_status_display",
            "status_changed",
            "published",
        )


class Query(graphene.ObjectType):
    simple_campaigns = DjangoFilterConnectionField(SimpleCampaignRunnerNode)
    interval_campaigns = DjangoFilterConnectionField(IntervalCampaignRunnerNode)
