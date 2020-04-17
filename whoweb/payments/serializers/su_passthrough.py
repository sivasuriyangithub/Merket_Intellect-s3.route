from djstripe import settings as djstripe_settings
from djstripe.models import Customer
from djstripe.sync import sync_subscriber
from rest_framework import serializers
from slugify import slugify

from whoweb.contrib.graphene_django.fields import NodeRelatedField
from whoweb.contrib.rest_framework.fields import IdOrHyperlinkedRelatedField
from whoweb.contrib.rest_framework.serializers import IdOrHyperlinkedModelSerializer
from whoweb.users.models import Seat, UserProfile, Group
from ..models import WKPlan


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
    customer_id = serializers.CharField(write_only=True, required=False)
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
    billing_account = IdOrHyperlinkedRelatedField(
        view_name="billingaccount-detail",
        source="billing.organization",
        lookup_field="public_id",
        default=None,
        read_only=True,
    )
    billing_seat = IdOrHyperlinkedRelatedField(
        view_name="billingaccountmember-detail",
        source="billing",
        lookup_field="public_id",
        default=None,
        read_only=True,
    )

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
            "billing_account",
            "billing_seat",
            "user",
            "customer_id",
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
        billing_account_name = f"{email} Primary ({xperweb_id})"
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

        if existing_customer := validated_data.get("customer_id"):
            _, created = Customer.objects.get_or_create(
                id=existing_customer,
                livemode=djstripe_settings.STRIPE_LIVE_MODE,
                defaults={
                    "subscriber": billing_account,
                    "balance": 0,
                    "delinquent": False,
                },
            )
            if created:
                customer = sync_subscriber(billing_account)
                subscriber_key = djstripe_settings.SUBSCRIBER_CUSTOMER_KEY
                if subscriber_key not in ("", None):
                    customer.metadata = customer.metadata or {}
                    customer.metadata[subscriber_key] = billing_account.pk
                    customer.save()
        seat.refresh_from_db()
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


class AdminBillingAccountSerializer(IdOrHyperlinkedModelSerializer):
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
    billing_account = IdOrHyperlinkedRelatedField(
        view_name="billingaccount-detail",
        source="billing.organization",
        lookup_field="public_id",
        default=None,
        read_only=True,
    )
    billing_seat = IdOrHyperlinkedRelatedField(
        view_name="billingaccountmember-detail",
        source="billing",
        lookup_field="public_id",
        default=None,
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
            "billing_account",
            "billing_seat",
            "user",
            "xperweb_id",
            "group_name",
            "group_id",
            "first_name",
            "last_name",
            "email",
        ]

    def create(self, validated_data):
        from whoweb.payments.models import BillingAccount

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
        billing_account_name = f"{email} Primary ({xperweb_id})"
        billing_account, _ = BillingAccount.objects.get_or_create(
            name=billing_account_name, slug=slugify(billing_account_name), group=group,
        )
        billing_member, _ = billing_account.get_or_add_user(
            user=profile.user, seat=seat
        )
        seat.refresh_from_db()
        return seat
