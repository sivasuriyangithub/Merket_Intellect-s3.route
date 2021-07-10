import django_filters
import graphene
from django_filters.rest_framework import OrderingFilter
from graphene import relay
from graphene_django.filter import DjangoFilterConnectionField, GlobalIDFilter
from rest_framework.permissions import IsAuthenticated

from whoweb.contrib.graphene_django.types import GuardedObjectType
from whoweb.contrib.rest_framework.filters import TagsFilter, ObscureIdFilterSet
from whoweb.contrib.rest_framework.permissions import IsSuperUser, ObjectPermissions
from whoweb.payments.permissions import MemberOfBillingAccountPermissionsFilter
from . import models


class CampaignObjectFilter(ObscureIdFilterSet):
    billing_seat = GlobalIDFilter(field_name="billing_seat__public_id")
    status = django_filters.TypedChoiceFilter(
        choices=[
            (c.value, c.name)
            for c in models.base.ColdemailBaseModel.CampaignObjectStatusOptions
        ],
        coerce=lambda x: getattr(
            models.base.ColdemailBaseModel.CampaignObjectStatusOptions, x
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


class CampaignMessageFilter(CampaignObjectFilter):
    class Meta:
        model = models.CampaignMessage
        fields = (
            "status",
            "published",
            "billing_seat",
            "id",
        )

    order_by = OrderingFilter(fields=("title",))


class CampaignMessageTemplateFilter(CampaignObjectFilter):
    class Meta:
        model = models.CampaignMessageTemplate
        fields = (
            "status",
            "published",
            "billing_seat",
            "id",
        )


class CampaignMessageNode(GuardedObjectType):
    class Meta:
        model = models.CampaignMessage
        interfaces = (relay.Node,)
        filterset_class = CampaignMessageFilter
        permission_classes = [IsSuperUser | IsAuthenticated]
        filter_backends = (MemberOfBillingAccountPermissionsFilter,)
        fields = (
            "billing_seat",
            "title",
            "subject",
            "html_content",
            "plain_content",
            "modified",
            "published",
            "status",
            # "status_name",
            "status_changed",
        )


class CampaignMessageTemplateNode(GuardedObjectType):
    tags = graphene.List(graphene.String, resolver=lambda x, i: x.tags.all())

    class Meta:
        model = models.CampaignMessageTemplate
        interfaces = (relay.Node,)
        filterset_class = CampaignMessageTemplateFilter
        permission_classes = [IsSuperUser | IsAuthenticated]
        filter_backends = (MemberOfBillingAccountPermissionsFilter,)
        fields = (
            "billing_seat",
            "title",
            "subject",
            "html_content",
            "plain_content",
            "modified",
            "published",
            "status",
        )


class ProfileLogEntry(graphene.ObjectType):
    email = graphene.String()
    web_id = graphene.String(name="profile_id")


class Campaign(GuardedObjectType):
    click_log = graphene.List(ProfileLogEntry, name="clickProfiles")
    open_log = graphene.List(ProfileLogEntry, name="openProfiles")
    reply_log = graphene.List(ProfileLogEntry, name="replyProfiles")
    good_log = graphene.List(ProfileLogEntry, name="goodProfiles")
    sent_profiles = graphene.List(graphene.String)
    message = graphene.Field(CampaignMessageNode)

    class Meta:
        interfaces = (relay.Node,)
        model = models.ColdCampaign
        fields = (
            "billing_seat",
            "from_name",
            "message",
            "created",
            "modified",
            "send_time",
            "stats_fetched",
            "sent",
            "views",
            "clicks",
            "unique_clicks",
            "unique_views",
            "optouts",
            "good",
            "start_time",
            "end_time",
            "click_log",
            "open_log",
            "good_log",
            "reply_log",
            "sent_profiles",
            "status",
            # "status_name",
            "status_changed",
            "published",
        )

    def resolve_sent_profiles(self, info):
        return (profile.id for profile in self.campaign_list.export.get_profiles())


class SingleRecipientEmailFilter(CampaignObjectFilter):
    class Meta:
        model = models.SingleColdEmail
        fields = (
            "status",
            "published",
            "billing_seat",
            "id",
        )


class SingleRecipientEmail(GuardedObjectType):
    class Meta:
        interfaces = (relay.Node,)
        filterset_class = SingleRecipientEmailFilter
        permission_classes = [IsSuperUser | IsAuthenticated]
        filter_backends = (MemberOfBillingAccountPermissionsFilter,)
        model = models.SingleColdEmail
        fields = (
            "message",
            "tags",
            "email",
            "send_date",
            "test",
            "use_credits_method",
            "billing_seat",
            "views",
            "clicks",
            "optouts",
            "from_name",
            "status",
            "modified",
            "published",
        )


class Query(graphene.ObjectType):
    campaign_messages = DjangoFilterConnectionField(CampaignMessageNode)
    campaign_message_templates = DjangoFilterConnectionField(
        CampaignMessageTemplateNode
    )
    single_recipient_email = DjangoFilterConnectionField(SingleRecipientEmail)
