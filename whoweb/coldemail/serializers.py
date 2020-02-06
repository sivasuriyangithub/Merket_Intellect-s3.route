from rest_framework import serializers

from .models import CampaignMessage, ColdCampaign, CampaignList
from whoweb.search.serializers import FilteredSearchQuerySerializer


class CampaignMessageSerializer(serializers.HyperlinkedModelSerializer):
    status_name = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = CampaignMessage
        extra_kwargs = {
            "url": {"lookup_field": "public_id"},
            "seat": {"lookup_field": "public_id"},
        }
        fields = (
            "url",
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


class CampaignListSerializer(serializers.HyperlinkedModelSerializer):
    query = FilteredSearchQuerySerializer()
    status_name = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = CampaignList
        extra_kwargs = {
            "url": {"lookup_field": "public_id"},
            "seat": {"lookup_field": "public_id"},
        }
        fields = (
            "url",
            "seat",
            "name",
            "origin",
            "query",
            "status",
            "status_name",
            "status_changed",
            "published_at",
        )
        read_only_fields = ("status", "status_changed", "status_name", "published_at")


class CampaignSerializer(serializers.HyperlinkedModelSerializer):
    status_name = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = ColdCampaign
        extra_kwargs = {
            "url": {"lookup_field": "public_id"},
            "seat": {"lookup_field": "public_id"},
            "message": {"lookup_field": "public_id"},
            "campaign_list": {"lookup_field": "public_id"},
        }
        fields = (
            "url",
            "message",
            "campaign_list",
            "seat",
            "title",
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
        read_only_fields = (
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
