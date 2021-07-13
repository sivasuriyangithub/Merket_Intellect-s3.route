from rest_framework import serializers
from rest_framework_guardian.serializers import ObjectPermissionsAssignmentMixin

from whoweb.payments.models import BillingAccountMember
from whoweb.accounting.serializers import TransactionSerializer
from whoweb.contrib.rest_framework.fields import (
    IdOrHyperlinkedRelatedField,
    TagulousField,
    EnumField,
)
from whoweb.coldemail.serializers import CampaignSerializer
from whoweb.contrib.rest_framework.serializers import (
    IdOrHyperlinkedModelSerializer,
    TaggableMixin,
)
from whoweb.search.serializers import FilteredSearchQuerySerializer
from .models import (
    SendingRule,
    DripRecord,
    SimpleDripCampaignRunner,
    IntervalCampaignRunner,
)


class SendingRuleSerializer(IdOrHyperlinkedModelSerializer):

    trigger = EnumField(
        SendingRule.SendingRuleTriggerOptions, to_choice=lambda x: (x.name, x.name)
    )

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
    drip = CampaignSerializer(read_only=True)
    root = serializers.SlugRelatedField(slug_field="public_id", read_only=True)

    class Meta:
        model = DripRecord
        fields = ("root", "drip", "order")


class SendingRuleMixin(object):
    def update(self, validated_data):
        rules = validated_data.pop("sending_rules")
        runner = super().update(validated_data)
        SendingRule.objects.delete(runner=runner)
        for rule in rules:
            idx = rule.pop("index")
            SendingRule.objects.update_or_create(
                runner=runner, index=idx, defaults=rule,
            )
        runner.refresh_from_db()
        return runner

    def create(self, validated_data):
        rules = validated_data.pop("sending_rules")
        runner = super().create(validated_data)
        for rule in rules:
            idx = rule.pop("index")
            SendingRule.objects.update_or_create(
                runner=runner, index=idx, defaults=rule,
            )
        return runner


class SimpleDripCampaignRunnerSerializer(
    ObjectPermissionsAssignmentMixin,
    TaggableMixin,
    SendingRuleMixin,
    IdOrHyperlinkedModelSerializer,
):
    id = serializers.CharField(source="public_id", read_only=True)
    query = FilteredSearchQuerySerializer()
    billing_seat = IdOrHyperlinkedRelatedField(
        view_name="billingaccountmember-detail",
        lookup_field="public_id",
        queryset=BillingAccountMember.objects.all(),
        required=True,
    )
    campaigns = CampaignSerializer(many=True, read_only=True)
    drips = DripRecordSerializer(many=True, read_only=True, source="drip_records")
    sending_rules = SendingRuleSerializer(many=True)
    status_name = serializers.CharField(source="get_status_display", read_only=True)
    tags = TagulousField(required=False, many=True)
    transactions = TransactionSerializer(many=True, read_only=True)

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
            "saved_search",
            "billing_seat",
            "budget",
            "title",
            "tags",
            "sending_rules",
            "drips",
            "campaigns",
            "transactions",
            "status",
            "status_name",
            "status_changed",
            "published",
            "tracking_params",
            "use_credits_method",
            "open_credit_budget",
            "from_name",
            "created",
            "modified",
        ]
        read_only_fields = [
            "created",
            "modified",
            "drips",
            "status",
            "status_changed",
            "status_name",
            "published",
        ]

    def get_permissions_map(self, created):
        user = self.context["request"].user
        return {
            "view_simpledripcampaignrunner": [user],
            "change_simpledripcampaignrunner": [user],
            "delete_simpledripcampaignrunner": [user],
        }


class IntervalCampaignRunnerSerializer(
    ObjectPermissionsAssignmentMixin,
    TaggableMixin,
    SendingRuleMixin,
    IdOrHyperlinkedModelSerializer,
):
    id = serializers.CharField(source="public_id", read_only=True)
    query = FilteredSearchQuerySerializer()
    campaigns = CampaignSerializer(many=True, read_only=True)
    sending_rules = SendingRuleSerializer(many=True)
    status_name = serializers.CharField(source="get_status_display", read_only=True)
    billing_seat = IdOrHyperlinkedRelatedField(
        view_name="billingaccountmember-detail",
        lookup_field="public_id",
        queryset=BillingAccountMember.objects.all(),
        required=True,
    )
    tags = TagulousField(required=False, many=True)
    transactions = TransactionSerializer(many=True, read_only=True)

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
            "saved_search",
            "billing_seat",
            "budget",
            "title",
            "tags",
            "sending_rules",
            "drips",
            "campaigns",
            "transactions",
            "status",
            "status_name",
            "status_changed",
            "published",
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
            "published",
        ]

    def get_permissions_map(self, created):
        user = self.context["request"].user
        return {
            "view_intervaldripcampaignrunner": [user],
            "change_intervaldripcampaignrunner": [user],
            "delete_intervaldripcampaignrunner": [user],
        }
