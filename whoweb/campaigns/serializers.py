from rest_framework import serializers

from whoweb.contrib.rest_framework.fields import IdOrHyperlinkedRelatedField
from whoweb.users.models import Seat
from whoweb.coldemail.serializers import CampaignSerializer, TaggableMixin
from whoweb.contrib.rest_framework.serializers import IdOrHyperlinkedModelSerializer
from whoweb.search.serializers import FilteredSearchQuerySerializer
from .models import (
    SendingRule,
    DripRecord,
    SimpleDripCampaignRunner,
    IntervalCampaignRunner,
)


class SendingRuleSerializer(IdOrHyperlinkedModelSerializer):
    class Meta:
        model = SendingRule
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


class SendingRuleMixin(object):
    def create(self, validated_data):
        rules = validated_data.pop("sending_rules")
        runner = super().create(validated_data)
        for rule in rules:
            idx = rule.pop("index")
            SendingRule.objects.update_or_create(
                runner=runner, index=idx, defaults=rule,
            )
        runner.refresh_from_db(fields=("messages",))
        return runner


class SimpleDripCampaignRunnerSerializer(
    TaggableMixin, SendingRuleMixin, IdOrHyperlinkedModelSerializer
):
    id = serializers.CharField(source="public_id", read_only=True)
    query = FilteredSearchQuerySerializer()
    seat = IdOrHyperlinkedRelatedField(
        view_name="seat-detail",
        lookup_field="public_id",
        queryset=Seat.objects.all(),
        required=True,
        allow_null=False,
    )
    campaigns = CampaignSerializer(many=True, read_only=True)
    sending_rules = SendingRuleSerializer(many=True)
    status_name = serializers.CharField(source="get_status_display", read_only=True)
    tags = serializers.ListSerializer(child=serializers.CharField(), required=False)

    class Meta:
        model = SimpleDripCampaignRunner
        extra_kwargs = {
            "url": {"lookup_field": "public_id"},
        }
        depth = 1
        fields = [
            "url",
            "id",
            "query",
            "seat",
            "budget",
            "title",
            "tags",
            "sending_rules",
            "drips",
            "campaigns",
            "status",
            "status_name",
            "status_changed",
            "published_at",
            "tracking_params",
            "use_credits_method",
            "open_credit_budget",
            "from_name",
        ]
        read_only_fields = [
            "drips",
            "status",
            "status_changed",
            "status_name",
            "published_at",
        ]


class IntervalCampaignRunnerSerializer(
    TaggableMixin, SendingRuleMixin, IdOrHyperlinkedModelSerializer
):
    id = serializers.CharField(source="public_id", read_only=True)
    query = FilteredSearchQuerySerializer()
    campaigns = CampaignSerializer(many=True, read_only=True)
    sending_rules = SendingRuleSerializer(many=True)
    status_name = serializers.CharField(source="get_status_display", read_only=True)
    seat = IdOrHyperlinkedRelatedField(
        view_name="seat-detail",
        lookup_field="public_id",
        queryset=Seat.objects.all(),
        required=False,
        allow_null=True,
    )
    tags = serializers.ListSerializer(child=serializers.CharField(), required=False)

    class Meta:
        model = IntervalCampaignRunner
        depth = 1
        extra_kwargs = {
            "url": {"lookup_field": "public_id"},
        }
        fields = [
            "url",
            "id",
            "query",
            "seat",
            "budget",
            "title",
            "tags",
            "sending_rules",
            "drips",
            "campaigns",
            "status",
            "status_name",
            "status_changed",
            "published_at",
            "tracking_params",
            "interval_hours",
            "max_sends",
            "from_name",
        ]
        read_only_fields = [
            "drips",
            "campaigns",
            "status",
            "status_changed",
            "status_name",
            "published_at",
        ]
