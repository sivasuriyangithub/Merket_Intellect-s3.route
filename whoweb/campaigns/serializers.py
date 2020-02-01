from rest_framework import serializers

from whoweb.search.serializers import FilteredSearchQuerySerializer
from .models import (
    SendingRule,
    DripRecord,
    SimpleDripCampaignRunner,
    IntervalCampaignRunner,
)


class SendingRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = SendingRule
        depth = 1


class DripRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = DripRecord
        depth = 1


class BaseRunnerSerializer(serializers.HyperlinkedModelSerializer):
    query = FilteredSearchQuerySerializer()
    status_name = serializers.CharField(source="get_status_display", read_only=True)
    FIELDS = [
        "url",
        "query",
        "seat",
        "messages",
        "drips",
        "campaigns",
        "status",
        "status_name",
        "status_changed",
        "published_at",
        "tracking_params",
    ]
    READ_ONLY_FIELDS = [
        "drips",
        "campaigns",
        "status",
        "status_changed",
        "status_name",
        "published_at",
    ]


class SimpleDripCampaignRunnerSerializer(BaseRunnerSerializer):
    class Meta:
        model = SimpleDripCampaignRunner
        # depth = 1
        fields = BaseRunnerSerializer.FIELDS + [
            "use_credits_method",
            "open_credit_budget",
            "preset_campaign_list",
        ]
        read_only_fields = BaseRunnerSerializer.READ_ONLY_FIELDS


class IntervalCampaignRunnerSerializer(BaseRunnerSerializer):
    class Meta:
        model = IntervalCampaignRunner
        depth = 1
        fields = BaseRunnerSerializer.FIELDS + [
            "interval_hours",
            "max_sends",
        ]
        read_only_fields = BaseRunnerSerializer.READ_ONLY_FIELDS
