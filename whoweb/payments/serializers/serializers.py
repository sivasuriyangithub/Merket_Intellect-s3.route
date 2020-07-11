from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from slugify import slugify

from whoweb.contrib.graphene_django.fields import NodeRelatedField
from whoweb.contrib.rest_framework.fields import IdOrHyperlinkedRelatedField
from whoweb.contrib.rest_framework.serializers import IdOrHyperlinkedModelSerializer
from whoweb.users.models import Group
from .stripe import SubscriptionSerializer, StripePlanSerializer
from ..models import BillingAccount, BillingAccountMember, WKPlan, WKPlanPreset

User = get_user_model()


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
    network = IdOrHyperlinkedRelatedField(
        view_name="group-detail",
        lookup_field="public_id",
        queryset=Group.objects.all(),
    )
    created_by = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = BillingAccount
        extra_kwargs = {
            "url": {"lookup_field": "public_id"},
            "plan": {"lookup_field": "public_id"},
        }
        depth = 2
        fields = (
            "customer_type",
            "network",
            "name",
            "slug",
            "url",
            "id",
            "graph_id",
            "plan",
            "credit_pool",
            "subscription",
            "created_by",
        )
        read_only_fields = (
            "slug",
            "plan",
            "credit_pool",
            "subscription",
            "customer_type",
        )

    def create(self, validated_data):
        creator = validated_data.pop("created_by")
        name = validated_data["name"]
        account, created = BillingAccount.objects.get_or_create(
            slug=slugify(name), **validated_data
        )
        creator.groups.add(*account.default_admin_permission_groups)
        return account


class PlanQuantitySerializer(serializers.Serializer):
    stripe_id = serializers.CharField()
    quantity = serializers.IntegerField()


class BillingAccountSubscriptionSerializer(serializers.Serializer):
    """A serializer used to create and update a WhoKnows Subscription."""

    stripe_token = serializers.CharField(
        max_length=200, required=False, write_only=True
    )
    plan = serializers.CharField(source="plan_id", write_only=True, required=True)
    items = PlanQuantitySerializer(many=True, write_only=True)
    trial_days = serializers.IntegerField(
        required=False, default=None, allow_null=True, write_only=True
    )
    customer_type = serializers.CharField(write_only=True, required=False)
    charge_immediately = serializers.NullBooleanField(required=False, write_only=True)
    initiated_by = serializers.HiddenField(default=serializers.CurrentUserDefault())


class ManageMemberCreditsSerializer(serializers.Serializer):
    credits = serializers.IntegerField(min_value=0, default=0, initial=0)
    pool = serializers.BooleanField(default=False, initial=False, required=False)
    billing_seat = IdOrHyperlinkedRelatedField(
        view_name="billingaccountmember-detail",
        lookup_field="public_id",
        queryset=BillingAccountMember.objects.all(),
    )

    def validate(self, attrs):
        if attrs.get("pool", False) and attrs.get("credits", 0) > 0:
            raise ValidationError(
                "You may not set credits for a member using the account credit pool. "
                "Either set pool to false or set credits to 0."
            )
        return attrs


class BillingAccountMemberSerializer(IdOrHyperlinkedModelSerializer):
    id = serializers.CharField(source="public_id", read_only=True)
    graph_id = NodeRelatedField("BillingAccountMemberNode", source="public_id")
    billing_account = IdOrHyperlinkedRelatedField(
        source="organization",
        view_name="billingaccount-detail",
        lookup_field="public_id",
        queryset=BillingAccount.objects.all(),
    )
    credits = serializers.IntegerField(required=False)
    subscription = SubscriptionSerializer(
        read_only=True, source="organization.subscription"
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
            "subscription",
            "seat",
            "pool_credits",
            "credits",
        )

    def create(self, validated_data):
        print(validated_data)
        billing_account: BillingAccount = validated_data["organization"]
        seat = validated_data["seat"]
        member, created = billing_account.get_or_add_user(
            seat.user, seat=seat, pool_credits=validated_data.get("pool_credits", True)
        )
        if not created:
            return member

        if member.pool_credits is False and validated_data.get("credits"):
            billing_account.allocate_credits_to_member(
                member=member, amount=validated_data["credits"]
            )

        return member
