from rest_framework import serializers
from slugify import slugify

from whoweb.contrib.graphene_django.fields import NodeRelatedField
from whoweb.contrib.rest_framework.fields import IdOrHyperlinkedRelatedField
from whoweb.contrib.rest_framework.serializers import IdOrHyperlinkedModelSerializer
from whoweb.users.models import Seat, UserProfile, Group
from .models import WKPlan


class PlanSerializer(IdOrHyperlinkedModelSerializer):
    id = serializers.CharField(source="public_id", read_only=True)

    class Meta:
        model = WKPlan
        extra_kwargs = {"url": {"lookup_field": "public_id"}}
        fields = (
            "url",
            "id",
            "credits_per_enrich",
            "credits_per_work_email",
            "credits_per_personal_email",
            "credits_per_phone",
        )


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
        profile, _ = UserProfile.get_or_create(username=xperweb_id, email=email)
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
        return super().update(instance, validated_data)
