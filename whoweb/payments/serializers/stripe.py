from djstripe.models import Subscription, SubscriptionItem, Plan, Product
from rest_framework import serializers

from whoweb.contrib.rest_framework.fields import IdOrHyperlinkedRelatedField
from ..models import BillingAccount


class AddPaymentSourceSerializer(serializers.Serializer):
    stripe_token = serializers.CharField(max_length=200)
    billing_account = IdOrHyperlinkedRelatedField(
        view_name="billingaccount-detail",
        lookup_field="public_id",
        queryset=BillingAccount.objects.all(),
        required=True,
    )


class StripeProductSerializer(serializers.ModelSerializer):
    class Meta:
        """Model class options."""

        model = Product
        fields = ["id", "name", "metadata", "unit_label"]
        read_only_fields = fields


class StripePlanSerializer(serializers.ModelSerializer):
    """A serializer used for the Plan model."""

    product = StripeProductSerializer(read_only=True)

    class Meta:
        """Model class options."""

        model = Plan
        fields = [
            "id",
            "amount",
            "currency",
            "interval",
            "interval_count",
            "product",
            "metadata",
            "tiers",
            "trial_period_days",
        ]
        read_only_fields = fields


class SubscriptionItemSerializer(serializers.ModelSerializer):
    """A serializer used for the SubscriptionItem model."""

    plan = StripePlanSerializer()

    class Meta:
        """Model class options."""

        model = SubscriptionItem
        fields = [
            "created",
            "plan",
            "quantity",
            "metadata",
            "description",
        ]
        read_only_fields = fields


class SubscriptionSerializer(serializers.ModelSerializer):
    """A serializer used for the Subscription model."""

    items = SubscriptionItemSerializer(many=True)
    can_charge = serializers.BooleanField(source="customer.can_charge", read_only=True)
    is_valid = serializers.BooleanField(read_only=True)

    class Meta:
        """Model class options."""

        depth = 2
        model = Subscription
        fields = [
            "created",
            "description",
            "metadata",
            "collection_method",
            "billing_cycle_anchor",
            "cancel_at_period_end",
            "canceled_at",
            "current_period_end",
            "current_period_start",
            "days_until_due",
            "ended_at",
            "plan",
            "quantity",
            "start_date",
            "status",
            "trial_end",
            "trial_start",
            "items",
            "can_charge",
            "is_valid",
        ]
