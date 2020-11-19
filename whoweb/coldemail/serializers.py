from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

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


class CampaignMessageSerializer(TaggableMixin, IdOrHyperlinkedModelSerializer):
    status_name = serializers.CharField(source="get_status_display", read_only=True)
    id = serializers.CharField(source="public_id", read_only=True)
    tags = TagulousField(required=False)

    class Meta:
        model = CampaignMessage
        extra_kwargs = {
            "url": {"lookup_field": "public_id"},
            "billing_seat": {"lookup_field": "public_id"},
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


class CampaignMessageTemplateSerializer(TaggableMixin, IdOrHyperlinkedModelSerializer):
    id = serializers.CharField(source="public_id", read_only=True)
    tags = TagulousField(required=False)

    class Meta:
        model = CampaignMessageTemplate
        extra_kwargs = {
            "url": {"lookup_field": "public_id"},
            "billing_seat": {"lookup_field": "public_id"},
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


class CampaignListSerializer(TaggableMixin, IdOrHyperlinkedModelSerializer):
    query = FilteredSearchQuerySerializer()
    status_name = serializers.CharField(source="get_status_display", read_only=True)
    id = serializers.CharField(source="public_id", read_only=True)
    tags = TagulousField(required=False)

    class Meta:
        model = CampaignList
        extra_kwargs = {
            "url": {"lookup_field": "public_id"},
            "billing_seat": {"lookup_field": "public_id"},
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
            "pk",
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


class SingleColdEmailSerializer(TaggableMixin, IdOrHyperlinkedModelSerializer):
    tags = TagulousField(required=False)

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
            "billing_seat": {"lookup_field": "public_id"},
            "message": {"lookup_field": "public_id"},
        }

    def validate(self, attrs):
        seat = attrs.get("billing_seat")
        if seat and seat != attrs["message"].billing_seat:
            raise PermissionDenied
        return attrs
