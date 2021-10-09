import django_filters
import graphene
from django_filters.rest_framework import OrderingFilter
from graphene import relay
from graphene_django.filter import DjangoFilterConnectionField, GlobalIDFilter

from whoweb.search.schema import SearchExportNode
from whoweb.users.models import User
from whoweb.contrib.graphene_django.types import GuardedObjectType
from whoweb.contrib.rest_framework.filters import (
    TagsFilter,
    ObscureIdFilterSet,
    ObjectPermissionsFilter,
)
from whoweb.contrib.rest_framework.permissions import (
    IsSuperUser,
    ObjectPermissions,
    ObjectPassesTest,
)
from whoweb.payments.permissions import MemberOfBillingAccountPermissionsFilter
from . import models


def member_of_billing_account(viewer: User, base_model: models.base.ColdemailBaseModel):
    return viewer.payments_billingaccount.filter(
        pk=base_model.billing_seat.organization.pk
    ).exists()


CampaignObjectStatusChoices = graphene.Enum.from_enum(
    models.base.ColdemailBaseModel.CampaignObjectStatusOptions
)


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
    status = graphene.Field(CampaignObjectStatusChoices)

    class Meta:
        model = models.CampaignMessage
        interfaces = (relay.Node,)
        filterset_class = CampaignMessageFilter
        permission_classes = [
            ObjectPassesTest(member_of_billing_account)
            | IsSuperUser
            | ObjectPermissions
        ]
        filter_backends = (
            ObjectPermissionsFilter | MemberOfBillingAccountPermissionsFilter,
        )
        fields = (
            "billing_seat",
            "title",
            "subject",
            "html_content",
            "plain_content",
            "modified",
            "published",
            "status",
            "status_changed",
        )


class CampaignMessageTemplateNode(GuardedObjectType):
    tags = graphene.List(graphene.String, resolver=lambda x, i: x.tags.all())

    class Meta:
        model = models.CampaignMessageTemplate
        interfaces = (relay.Node,)
        filterset_class = CampaignMessageTemplateFilter
        permission_classes = [
            ObjectPassesTest(member_of_billing_account)
            | IsSuperUser
            | ObjectPermissions
        ]
        filter_backends = (
            ObjectPermissionsFilter | MemberOfBillingAccountPermissionsFilter,
        )
        fields = (
            "billing_seat",
            "title",
            "subject",
            "html_content",
            "plain_content",
            "modified",
            "published",
        )


class ProfileLogEntry(graphene.ObjectType):
    email = graphene.String()
    web_id = graphene.String(name="profile_id")


class Campaign(GuardedObjectType):
    search_export = graphene.Field(SearchExportNode)
    good_log = graphene.List(ProfileLogEntry, name="goodProfiles")
    open_log = graphene.List(ProfileLogEntry, name="openProfiles")
    click_log = graphene.List(ProfileLogEntry, name="clickProfiles")
    reply_log = graphene.List(ProfileLogEntry, name="replyProfiles")

    unique_good_profiles = graphene.List(ProfileLogEntry)
    unique_open_profiles = graphene.List(ProfileLogEntry)
    unique_click_profiles = graphene.List(ProfileLogEntry)
    unique_reply_profiles = graphene.List(ProfileLogEntry)

    sent_profiles = graphene.List(graphene.String)
    message = graphene.Field(CampaignMessageNode)
    status = graphene.Field(CampaignObjectStatusChoices)

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
            "search_export",
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
            "unique_good_profiles",
            "unique_open_profiles",
            "unique_click_profiles",
            "unique_reply_profiles",
            "sent_profiles",
            "status",
            "status_changed",
            "published",
        )

    def resolve_sent_profiles(self, info):
        return (profile.id for profile in self.campaign_list.export.get_profiles())

    def resolve_click_log(self, info):
        return self.click_log.get("log", []) if self.click_log else []

    def resolve_open_log(self, info):
        return self.open_log.get("log", []) if self.open_log else []

    def resolve_reply_log(self, info):
        return self.reply_log.get("log", []) if self.reply_log else []

    def resolve_good_log(self, info):
        return self.good_log.get("log", []) if self.good_log else []

    def resolve_unique_click_profiles(self, info):
        return self.click_log.get("unique_log", []) if self.click_log else []

    def resolve_unique_open_profiles(self, info):
        return self.open_log.get("unique_log", []) if self.open_log else []

    def resolve_unique_reply_profiles(self, info):
        return self.reply_log.get("unique_log", []) if self.reply_log else []

    def resolve_unique_good_profiles(self, info):
        return self.good_log.get("unique_log", []) if self.good_log else []


class SingleRecipientEmailFilter(CampaignObjectFilter):
    class Meta:
        model = models.SingleColdEmail
        fields = (
            "status",
            "published",
            "billing_seat",
            "id",
        )

    order_by = OrderingFilter(fields=("modified",))


class SingleRecipientEmail(GuardedObjectType):
    status = graphene.Field(CampaignObjectStatusChoices)

    class Meta:
        interfaces = (relay.Node,)
        filterset_class = SingleRecipientEmailFilter
        permission_classes = [
            ObjectPassesTest(member_of_billing_account)
            | IsSuperUser
            | ObjectPermissions
        ]
        filter_backends = (MemberOfBillingAccountPermissionsFilter,)
        model = models.SingleColdEmail
        fields = (
            "message",
            "tags",
            "email",
            "send_date",
            "test",
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
