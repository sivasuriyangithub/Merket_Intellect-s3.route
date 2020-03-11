from rest_framework import serializers
from slugify import slugify

from whoweb.contrib.graphene_django.fields import NodeRelatedField
from whoweb.contrib.rest_framework.fields import IdOrHyperlinkedRelatedField
from whoweb.contrib.rest_framework.serializers import IdOrHyperlinkedModelSerializer
from whoweb.users.models import Seat, UserProfile, Group
from .models import WKPlan, BillingAccount, BillingAccountMember


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
            "credits_per_enrich",
            "credits_per_work_email",
            "credits_per_personal_email",
            "credits_per_phone",
        )
        read_only_fields = fields


class BillingAccountSerializer(IdOrHyperlinkedModelSerializer):
    id = serializers.CharField(source="public_id", read_only=True)
    graph_id = NodeRelatedField("BillingAccountNode", source="public_id")

    class Meta:
        model = BillingAccount
        extra_kwargs = {
            "url": {"lookup_field": "public_id"},
            "plan": {"lookup_field": "public_id"},
        }
        fields = ("url", "id", "graph_id", "plan", "credit_pool", "trial_credit_pool")
        read_only_fields = fields


class BillingAccountMemberSerializer(IdOrHyperlinkedModelSerializer):
    id = serializers.CharField(source="public_id", read_only=True)
    graph_id = NodeRelatedField("BillingAccountMemberNode", source="public_id")
    billing_account = IdOrHyperlinkedRelatedField(
        source="organization",
        view_name="billing_account-detail",
        lookup_field="public_id",
        read_only=True,
    )
    plan = IdOrHyperlinkedRelatedField(
        view_name="wkplan-detail", lookup_field="public_id", read_only=True,
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


class PlanQuantitySerializer(serializers.Serializer):
    stripe_id = serializers.CharField()
    quantity = serializers.IntegerField()


class CreateSubscriptionSerializer(serializers.Serializer):
    """A serializer used to create a Subscription."""

    stripe_token = serializers.CharField(max_length=200)
    plan = serializers.CharField(max_length=50)
    items = PlanQuantitySerializer()
    charge_immediately = serializers.NullBooleanField(required=False)


class UpdateSubscriptionSerializer(serializers.Serializer):
    """A serializer used to create a Subscription."""

    plan = serializers.CharField(max_length=50)
    items = PlanQuantitySerializer()
    charge_immediately = serializers.NullBooleanField(required=False)


class AdminBillingSeatSerializer(IdOrHyperlinkedModelSerializer):
    created_by = serializers.HiddenField(default=serializers.CurrentUserDefault())
    graph_id = NodeRelatedField("SeatNode", source="public_id")
    id = serializers.CharField(source="public_id", read_only=True)
    network = IdOrHyperlinkedRelatedField(
        source="organization",
        view_name="group-detail",
        lookup_field="public_id",
        read_only=True,
    )
    user = IdOrHyperlinkedRelatedField(
        source="user_profile",
        view_name="userprofile-detail",
        lookup_field="public_id",
        read_only=True,
    )
    xperweb_id = serializers.CharField(write_only=True, required=False)
    group_name = serializers.CharField(
        write_only=True, allow_null=True, allow_blank=True, required=False
    )
    group_id = serializers.CharField(write_only=True, required=False)
    first_name = serializers.CharField(
        write_only=True, required=False, allow_blank=True
    )
    last_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    email = serializers.EmailField(write_only=True, required=False)
    seat_credits = serializers.IntegerField(required=False)
    credits_per_enrich = serializers.IntegerField(write_only=True, required=False)
    credits_per_work_email = serializers.IntegerField(write_only=True, required=False)
    credits_per_personal_email = serializers.IntegerField(
        write_only=True, required=False
    )
    credits_per_phone = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = Seat
        extra_kwargs = {
            "url": {"lookup_field": "public_id"},
        }
        fields = [
            "display_name",
            "network",
            "created_by",
            "url",
            "id",
            "graph_id",
            "user",
            "xperweb_id",
            "group_name",
            "group_id",
            "first_name",
            "last_name",
            "email",
            "seat_credits",
            "credits_per_enrich",
            "credits_per_work_email",
            "credits_per_personal_email",
            "credits_per_phone",
        ]

    def create(self, validated_data):
        from whoweb.payments.models import BillingAccount, WKPlan

        group_id = validated_data["group_id"]
        group_name = validated_data.get("group_name") or group_id
        xperweb_id = validated_data["xperweb_id"]
        email = validated_data["email"]
        first_name = validated_data["first_name"]
        last_name = validated_data["last_name"]
        profile, _ = UserProfile.get_or_create(
            username=xperweb_id, email=email, first_name=first_name, last_name=last_name
        )
        group, _ = Group.objects.get_or_create(name=group_name, slug=slugify(group_id))
        seat, _ = group.get_or_add_user(
            user=profile.user, display_name=profile.user.get_full_name()
        )
        plan, _ = WKPlan.objects.get_or_create(
            credits_per_enrich=validated_data["credits_per_enrich"],
            credits_per_work_email=validated_data["credits_per_work_email"],
            credits_per_personal_email=validated_data["credits_per_personal_email"],
            credits_per_phone=validated_data["credits_per_phone"],
        )
        if group_id == "public":
            billing_account_name = f"{xperweb_id} Primary Billing Account"
        else:
            billing_account_name = f"{group_name} Primary Billing Account"
        billing_account, _ = BillingAccount.objects.update_or_create(
            name=billing_account_name,
            slug=slugify(billing_account_name),
            group=group,
            defaults=dict(plan=plan),
        )
        billing_member, _ = billing_account.get_or_add_user(
            user=profile.user, seat=seat
        )
        billing_member.seat_credits = validated_data["seat_credits"]
        billing_member.save()
        return seat

    def update(self, instance, validated_data):
        seat_credits = validated_data.get("seat_credits")
        if seat_credits is not None:
            instance.billing.seat_credits = seat_credits
            instance.billing.save()
        if all(
            [
                "credits_per_enrich" in validated_data,
                "credits_per_work_email" in validated_data,
                "credits_per_personal_email" in validated_data,
                "credits_per_phone" in validated_data,
            ]
        ):
            plan, _ = WKPlan.objects.get_or_create(
                credits_per_enrich=validated_data["credits_per_enrich"],
                credits_per_work_email=validated_data["credits_per_work_email"],
                credits_per_personal_email=validated_data["credits_per_personal_email"],
                credits_per_phone=validated_data["credits_per_phone"],
            )
            instance.billing.organization.plan = plan
            instance.billing.organization.save()
        return instance
