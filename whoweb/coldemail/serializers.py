from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from whoweb.contrib.rest_framework.serializers import IdOrHyperlinkedModelSerializer
from .models import (
    CampaignMessage,
    ColdCampaign,
    CampaignList,
    CampaignMessageTemplate,
    SingleColdEmail,
)
from whoweb.search.serializers import FilteredSearchQuerySerializer


class CampaignMessageSerializer(IdOrHyperlinkedModelSerializer):
    status_name = serializers.CharField(source="get_status_display", read_only=True)
    id = serializers.CharField(source="public_id", read_only=True)

    class Meta:
        model = CampaignMessage
        extra_kwargs = {
            "url": {"lookup_field": "public_id"},
            "seat": {"lookup_field": "public_id"},
        }
        fields = (
            "url",
            "id",
            "seat",
            "title",
            "subject",
            "plain_content",
            "html_content",
            "editor",
            "status",
            "status_name",
            "status_changed",
            "published_at",
        )
        read_only_fields = ("status", "status_changed", "status_name", "published_at")


class CampaignMessageTemplateSerializer(IdOrHyperlinkedModelSerializer):
    id = serializers.CharField(source="public_id", read_only=True)

    class Meta:
        model = CampaignMessageTemplate
        extra_kwargs = {
            "url": {"lookup_field": "public_id"},
            "seat": {"lookup_field": "public_id"},
        }
        fields = (
            "url",
            "id",
            "seat",
            "title",
            "subject",
            "plain_content",
            "html_content",
            "editor",
        )


class CampaignListSerializer(IdOrHyperlinkedModelSerializer):
    query = FilteredSearchQuerySerializer()
    status_name = serializers.CharField(source="get_status_display", read_only=True)
    id = serializers.CharField(source="public_id", read_only=True)

    class Meta:
        model = CampaignList
        extra_kwargs = {
            "url": {"lookup_field": "public_id"},
            "seat": {"lookup_field": "public_id"},
        }
        fields = (
            "url",
            "id",
            "seat",
            "name",
            "origin",
            "description",
            "query",
            "status",
            "status_name",
            "status_changed",
            "published_at",
        )
        read_only_fields = ("status", "status_changed", "status_name", "published_at")


class CampaignSerializer(serializers.ModelSerializer):
    status_name = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = ColdCampaign
        fields = (
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
            "published_at",
        )
        read_only_fields = fields


class SingleColdEmailSerializer(IdOrHyperlinkedModelSerializer):
    class Meta:
        model = SingleColdEmail
        fields = (
            "url",
            "public_id",
            "message",
            "email",
            "send_date",
            "test",
            "use_credits_method",
            "seat",
            "views",
            "clicks",
            "optouts",
        )
        extra_kwargs = {
            "url": {"lookup_field": "public_id"},
            "seat": {"lookup_field": "public_id"},
            "message": {"lookup_field": "public_id"},
        }

    def validate(self, attrs):
        seat = attrs.get("seat")
        if seat and seat != attrs["message"].seat:
            raise PermissionDenied
        return attrs
