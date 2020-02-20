from rest_framework import serializers

from whoweb.contrib.rest_framework.serializers import IdOrHyperlinkedModelSerializer
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
        fields = (
            "message",
            "index",
            "trigger",
            "send_datetime",
            "send_delta",
            "include_previous",
        )
        extra_kwargs = {
            "message": {"lookup_field": "public_id"},
        }


class DripRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = DripRecord
        depth = 1
        fields = ("root", "drip", "order")
        extra_kwargs = {
            "root": {"lookup_field": "public_id"},
            "drip": {"lookup_field": "public_id"},
        }


class BaseRunnerSerializer(IdOrHyperlinkedModelSerializer):
    id = serializers.CharField(source="public_id", read_only=True)
    query = FilteredSearchQuerySerializer()
    sending_rules = SendingRuleSerializer(many=True)
    status_name = serializers.CharField(source="get_status_display", read_only=True)
    FIELDS = [
        "url",
        "id",
        "query",
        "seat",
        "budget",
        "sending_rules",
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

    def create(self, validated_data):
        rules = validated_data.pop("sending_rules")
        runner = self.Meta.model.objects.create(**validated_data)
        for rule in rules:
            idx = rule.pop("index")
            msg = rule.pop("message")
            SendingRule.objects.update_or_create(
                runner=runner, index=idx, defaults=rule,
            )
        runner.refresh_from_db(fields=("messages",))
        return runner


class SimpleDripCampaignRunnerSerializer(BaseRunnerSerializer):
    class Meta:
        model = SimpleDripCampaignRunner
        extra_kwargs = {
            "url": {"lookup_field": "public_id"},
            "seat": {"lookup_field": "public_id"},
            "campaigns": {"lookup_field": "public_id"},
            "drips": {"lookup_field": "public_id"},
            "messages": {"lookup_field": "public_id"},
        }
        fields = BaseRunnerSerializer.FIELDS + [
            "use_credits_method",
            "open_credit_budget",
            "preset_campaign_list",
        ]
        read_only_fields = BaseRunnerSerializer.READ_ONLY_FIELDS


class IntervalCampaignRunnerSerializer(BaseRunnerSerializer):
    class Meta:
        model = IntervalCampaignRunner
        extra_kwargs = {
            "url": {"lookup_field": "public_id"},
            "seat": {"lookup_field": "public_id"},
            "campaigns": {"lookup_field": "public_id"},
            "drips": {"lookup_field": "public_id"},
            "messages": {"lookup_field": "public_id"},
        }
        fields = BaseRunnerSerializer.FIELDS + [
            "interval_hours",
            "max_sends",
        ]
        read_only_fields = BaseRunnerSerializer.READ_ONLY_FIELDS
