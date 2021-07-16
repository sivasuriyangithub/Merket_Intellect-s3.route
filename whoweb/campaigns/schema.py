import django_filters
import graphene
from django_filters.rest_framework import FilterSet, OrderingFilter
from graphene import relay
from graphene.types.generic import GenericScalar
from graphene_django import DjangoListField
from graphene_django.filter import DjangoFilterConnectionField, GlobalIDFilter
from rest_framework.permissions import IsAuthenticated

from whoweb.users.models import User
from whoweb.campaigns import models
from whoweb.coldemail.schema import Campaign
from whoweb.contrib.graphene_django.types import GuardedObjectType
from whoweb.contrib.rest_framework.filters import TagsFilter, ObscureIdFilterSet
from whoweb.contrib.rest_framework.permissions import (
    IsSuperUser,
    ObjectPermissions,
    ObjectPassesTest,
)
from whoweb.payments.permissions import MemberOfBillingAccountPermissionsFilter
from whoweb.search.schema import FilteredSearchQueryObjectType

SendingRuleTriggerChoices = graphene.Enum.from_enum(
    models.SendingRule.SendingRuleTriggerOptions
)
CampaignRunnerStatusChoices = graphene.Enum.from_enum(
    models.BaseCampaignRunner.CampaignRunnerStatusOptions
)


def member_of_billing_account(viewer: User, campaign_runner: models.BaseCampaignRunner):
    return viewer.payments_billingaccount.filter(
        pk=campaign_runner.billing_seat.organization.pk
    ).exists()


class CampaignRunnerFilter(ObscureIdFilterSet):
    billing_seat = GlobalIDFilter(field_name="billing_seat__public_id")
    status = django_filters.TypedChoiceFilter(
        choices=[
            (s.value, s.name)
            for s in models.BaseCampaignRunner.CampaignRunnerStatusOptions
        ],
        coerce=lambda x: getattr(
            models.BaseCampaignRunner.CampaignRunnerStatusOptions, x
        ),
    )
    published = django_filters.DateRangeFilter(field_name="published",)
    published_after = django_filters.DateFilter(
        field_name="published", lookup_expr="gt"
    )
    published_before = django_filters.DateFilter(
        field_name="published", lookup_expr="lt"
    )
    tags = TagsFilter(field_name="tags__name")
    order_by = OrderingFilter(fields=("modified",))

    class Meta:
        model = models.BaseCampaignRunner
        fields = (
            "status",
            "published",
            "billing_seat",
            "id",
        )


class SendingRule(GuardedObjectType):
    trigger = graphene.Field(SendingRuleTriggerChoices)

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
    campaigns = DjangoListField(Campaign)
    tags = graphene.List(graphene.String, resolver=lambda x, i: x.tags.all())
    transactions = GenericScalar()
    tracking_params = graphene.List(TrackingParam)
    status = graphene.Field(CampaignRunnerStatusChoices)

    class Meta:
        model = models.SimpleDripCampaignRunner
        interfaces = (relay.Node,)
        filterset_class = CampaignRunnerFilter
        permission_classes = [
            ObjectPassesTest(member_of_billing_account)
            | IsSuperUser
            | ObjectPermissions
        ]
        filter_backends = (MemberOfBillingAccountPermissionsFilter,)
        fields = (
            "billing_seat",
            "budget",
            "query",
            "saved_search",
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
    campaigns = DjangoListField(Campaign)
    tags = graphene.List(graphene.String, resolver=lambda x, i: x.tags.all())
    transactions = GenericScalar()
    tracking_params = graphene.List(TrackingParam)
    status = graphene.Field(CampaignRunnerStatusChoices)

    class Meta:
        model = models.IntervalCampaignRunner
        interfaces = (relay.Node,)
        filterset_class = CampaignRunnerFilter
        permission_classes = [
            ObjectPassesTest(member_of_billing_account)
            | IsSuperUser
            | ObjectPermissions
        ]
        filter_backends = (MemberOfBillingAccountPermissionsFilter,)

        fields = (
            "query",
            "saved_search",
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
