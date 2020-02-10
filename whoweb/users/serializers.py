from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework_guardian.serializers import ObjectPermissionsAssignmentMixin
from slugify import slugify

from whoweb.contrib.rest_framework.fields import IdOrHyperlinkedRelatedField
from whoweb.contrib.rest_framework.serializers import IdOrHyperlinkedModelSerializer
from whoweb.contrib.graphene_django.fields import NodeRelatedField
from .models import Seat, DeveloperKey, Group, UserProfile

User = get_user_model()


class UserSerializer(IdOrHyperlinkedModelSerializer):
    graph_id = NodeRelatedField("UserNode", source="public_id")
    id = serializers.CharField(source="public_id", read_only=True)

    class Meta:
        model = User
        extra_kwargs = {"url": {"lookup_field": "public_id"}}
        fields = ("username", "url", "id", "graph_id", "email")
        read_only_fields = fields


class NetworkSerializer(IdOrHyperlinkedModelSerializer):
    graph_id = NodeRelatedField("NetworkNode", source="public_id")
    id = serializers.CharField(source="public_id", read_only=True)

    class Meta:
        model = Group
        extra_kwargs = {"url": {"lookup_field": "public_id"}}
        fields = ("name", "slug", "url", "id", "graph_id")
        read_only_fields = fields


class SeatSerializer(ObjectPermissionsAssignmentMixin, IdOrHyperlinkedModelSerializer):
    created_by = serializers.HiddenField(default=serializers.CurrentUserDefault())
    network = IdOrHyperlinkedRelatedField(
        source="organization",
        view_name="group-detail",
        lookup_field="public_id",
        queryset=Group.objects.all(),
    )
    graph_id = NodeRelatedField("SeatNode", source="public_id")
    id = serializers.CharField(source="public_id", read_only=True)

    class Meta:
        model = Seat
        extra_kwargs = {
            "url": {"lookup_field": "public_id"},
            "user": {"lookup_field": "public_id"},
        }
        fields = (
            "display_name",
            "network",
            "created_by",
            "url",
            "id",
            "graph_id",
            "user",
        )

    def get_readonly_fields(self, *, obj=None):
        if obj:
            return ["network", "user"]
        else:
            return []

    def validate(self, attrs):
        user = attrs.pop("created_by")
        if not user.has_perm("add_seat", attrs["organization"]):
            raise PermissionDenied
        return attrs

    def get_permissions_map(self, created):
        seat_admin = self.instance.organization.seat_admin_authgroup
        seat_viewers = self.instance.organization.seat_viewers
        user = self.instance.user

        return {
            "users.view_seat": [seat_admin, seat_viewers, user],
            "users.change_seat": [seat_admin, user],
            "users.delete_seat": [seat_admin],
        }


class AdminBillingAdjustingSeatSerializer(SeatSerializer):
    xperweb_id = serializers.CharField(write_only=True, required=False)
    group_name = serializers.CharField(
        write_only=True, allow_null=True, allow_blank=True, required=False
    )
    group_id = serializers.CharField(write_only=True, required=False)
    email = serializers.EmailField(write_only=True, required=False)
    seat_credits = serializers.IntegerField(write_only=True, required=False)
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
            "user": {"lookup_field": "public_id"},
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
        read_only_fields = [
            "user",
            "network",
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


class DeveloperKeySerializer(
    ObjectPermissionsAssignmentMixin, IdOrHyperlinkedModelSerializer
):
    created_by = serializers.HiddenField(default=serializers.CurrentUserDefault())
    id = serializers.CharField(source="pk", read_only=True)
    graph_id = NodeRelatedField("DeveloperKeyNode", source="pk")
    network = IdOrHyperlinkedRelatedField(
        source="group",
        view_name="group-detail",
        lookup_field="public_id",
        queryset=Group.objects.all(),
    )

    class Meta:
        model = DeveloperKey
        extra_kwargs = {
            "url": {"lookup_field": "public_id"},
        }
        fields = [
            "id",
            "network",
            "api_key",
            "secret",
            "test_key",
            "created_by",
            "created",
            "url",
            "graph_id",
        ]
        read_only_fields = ["id", "api_key", "secret"]

    def validate(self, attrs):
        user = attrs["created_by"]
        if not user.has_perm("add_developerkeys", attrs["group"]):
            raise PermissionDenied
        return attrs

    def get_permissions_map(self, created):
        authGroup = self.instance.group.credentials_admin_authgroup
        return {"delete_developerkey": [authGroup], "view_developerkey": [authGroup]}
