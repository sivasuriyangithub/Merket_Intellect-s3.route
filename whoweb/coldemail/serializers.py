from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework_guardian.serializers import ObjectPermissionsAssignmentMixin

from whoweb.contrib.rest_framework.fields import TagulousField
from whoweb.contrib.rest_framework.serializers import (
    IdOrHyperlinkedModelSerializer,
    TaggableMixin,
)
from .models import (
    CampaignMessage,
    ColdCampaign,
    CampaignList,
    CampaignMessageTemplate,
    SingleColdEmail,
)
from whoweb.search.serializers import FilteredSearchQuerySerializer


class CampaignMessageSerializer(
    ObjectPermissionsAssignmentMixin, TaggableMixin, IdOrHyperlinkedModelSerializer
):
    status_name = serializers.CharField(source="get_status_display", read_only=True)
    id = serializers.CharField(source="public_id", read_only=True)
    tags = TagulousField(required=False, many=True)

    class Meta:
        model = CampaignMessage
        extra_kwargs = {
            "url": {"lookup_field": "public_id"},
            "billing_seat": {"lookup_field": "public_id", "required": True},
        }
        fields = (
            "url",
            "id",
            "billing_seat",
            "title",
            "subject",
            "plain_content",
            "html_content",
            "editor",
            "tags",
            "status",
            "status_name",
            "status_changed",
            "published",
        )
        read_only_fields = ("status", "status_changed", "status_name", "published")

    def get_permissions_map(self, created):
        user = self.context["request"].user
        return {
            "view_campaignmessage": [user],
            "change_campaignmessage": [user],
            "delete_campaignmessage": [user],
        }


class CampaignMessageTemplateSerializer(
    ObjectPermissionsAssignmentMixin, TaggableMixin, IdOrHyperlinkedModelSerializer
):
    id = serializers.CharField(source="public_id", read_only=True)
    tags = TagulousField(required=False, many=True)

    class Meta:
        model = CampaignMessageTemplate
        extra_kwargs = {
            "url": {"lookup_field": "public_id"},
            "billing_seat": {"lookup_field": "public_id", "required": True},
        }
        fields = (
            "url",
            "id",
            "billing_seat",
            "title",
            "tags",
            "subject",
            "plain_content",
            "html_content",
            "editor",
        )

    def get_permissions_map(self, created):
        user = self.context["request"].user
        return {
            "view_campaignmessagetemplate": [user],
            "change_campaignmessagetemplate": [user],
            "delete_campaignmessagetemplate": [user],
        }


class CampaignListSerializer(TaggableMixin, IdOrHyperlinkedModelSerializer):
    query = FilteredSearchQuerySerializer()
    status_name = serializers.CharField(source="get_status_display", read_only=True)
    id = serializers.CharField(source="public_id", read_only=True)
    tags = TagulousField(required=False, many=True)

    class Meta:
        model = CampaignList
        extra_kwargs = {
            "url": {"lookup_field": "public_id"},
            "billing_seat": {"lookup_field": "public_id", "required": True},
        }
        fields = (
            "url",
            "id",
            "billing_seat",
            "name",
            "tags",
            "origin",
            "description",
            "query",
            "status",
            "status_name",
            "status_changed",
            "published",
        )
        read_only_fields = ("status", "status_changed", "status_name", "published")


class CampaignSerializer(serializers.ModelSerializer):
    status_name = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = ColdCampaign
        fields = (
            "public_id",
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
            "status",
            "status_name",
            "status_changed",
            "published",
        )
        read_only_fields = fields


class SingleColdEmailSerializer(
    ObjectPermissionsAssignmentMixin, TaggableMixin, IdOrHyperlinkedModelSerializer
):
    tags = TagulousField(required=False, many=True)

    class Meta:
        model = SingleColdEmail
        fields = (
            "url",
            "public_id",
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
        )
        extra_kwargs = {
            "url": {"lookup_field": "public_id"},
            "billing_seat": {"lookup_field": "public_id", "required": True},
            "message": {"lookup_field": "public_id"},
        }

    def validate(self, attrs):
        seat = attrs.get("billing_seat")
        if seat and seat != attrs["message"].billing_seat:
            raise PermissionDenied
        return attrs

    def get_permissions_map(self, created):
        user = self.context["request"].user
        return {
            "view_singlecoldemail": [user],
            "change_singlecoldemail": [user],
            "delete_singlecoldemail": [user],
        }
