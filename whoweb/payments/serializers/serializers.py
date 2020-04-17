from rest_framework import serializers

from whoweb.contrib.graphene_django.fields import NodeRelatedField
from whoweb.contrib.rest_framework.fields import IdOrHyperlinkedRelatedField
from whoweb.contrib.rest_framework.serializers import IdOrHyperlinkedModelSerializer
from .stripe import SubscriptionSerializer, StripePlanSerializer
from ..models import BillingAccount, BillingAccountMember, WKPlan, WKPlanPreset


class PlanSerializer(IdOrHyperlinkedModelSerializer):
    id = serializers.CharField(source="public_id", read_only=True)
    graph_id = NodeRelatedField("PlanNode", source="public_id")

    class Meta:
        model = WKPlan
        extra_kwargs = {"url": {"lookup_field": "public_id"}}
        fields = (
            "url",
            "id",
            "graph_id",
            "marketing_name",
            "credits_per_enrich",
            "credits_per_work_email",
            "credits_per_personal_email",
            "credits_per_phone",
        )
        read_only_fields = fields


class PlanPresetSerializer(serializers.ModelSerializer):
    stripe_plans_monthly = StripePlanSerializer(many=True)
    stripe_plans_yearly = StripePlanSerializer(many=True)
    defaults = StripePlanSerializer(many=True)
    id = serializers.CharField(source="public_id", read_only=True)

    class Meta:
        model = WKPlanPreset
        depth = 3
        fields = [
            "id",
            "tag",
            "marketing_name",
            "defaults",
            "stripe_plans_monthly",
            "stripe_plans_yearly",
            "trial_days_allowed",
            "credits_per_enrich",
            "credits_per_work_email",
            "credits_per_personal_email",
            "credits_per_phone",
        ]
        read_only_fields = fields


class BillingAccountSerializer(IdOrHyperlinkedModelSerializer):
    id = serializers.CharField(source="public_id", read_only=True)
    graph_id = NodeRelatedField("BillingAccountNode", source="public_id")
    subscription = SubscriptionSerializer(read_only=True)
    plan = PlanSerializer(read_only=True)

    class Meta:
        model = BillingAccount
        extra_kwargs = {
            "url": {"lookup_field": "public_id"},
            "plan": {"lookup_field": "public_id"},
        }
        depth = 2
        fields = (
            "url",
            "id",
            "graph_id",
            "plan",
            "credit_pool",
            "trial_credit_pool",
            "subscription",
        )
        read_only_fields = fields


class BillingAccountMemberSerializer(IdOrHyperlinkedModelSerializer):
    id = serializers.CharField(source="public_id", read_only=True)
    graph_id = NodeRelatedField("BillingAccountMemberNode", source="public_id")
    billing_account = IdOrHyperlinkedRelatedField(
        source="organization",
        view_name="billingaccount-detail",
        lookup_field="public_id",
        read_only=True,
    )

    class Meta:
        model = BillingAccountMember
        extra_kwargs = {
            "url": {"lookup_field": "public_id"},
            "seat": {"lookup_field": "public_id"},
        }
        fields = (
            "url",
            "id",
            "graph_id",
            "billing_account",
            "seat",
            "pool_credits",
            "credits",
            "trial_credits",
        )
        read_only_fields = fields


class CreditChargeSerializer(serializers.Serializer):
    initiated_by = serializers.HiddenField(default=serializers.CurrentUserDefault())
    amount = serializers.IntegerField(min_value=0)
    billing_account = IdOrHyperlinkedRelatedField(
        source="organization",
        view_name="billingaccount-detail",
        lookup_field="public_id",
        read_only=True,
    )
    notes = serializers.CharField(allow_blank=True, required=False, default="")
