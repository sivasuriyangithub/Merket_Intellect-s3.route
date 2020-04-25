from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework_guardian.serializers import ObjectPermissionsAssignmentMixin

from whoweb.contrib.graphene_django.fields import NodeRelatedField
from whoweb.contrib.rest_framework.fields import IdOrHyperlinkedRelatedField
from whoweb.contrib.rest_framework.serializers import IdOrHyperlinkedModelSerializer
from .models import Seat, DeveloperKey, Group, UserProfile


class UserSerializer(IdOrHyperlinkedModelSerializer):
    graph_id = NodeRelatedField("UserNode", source="public_id")
    id = serializers.CharField(source="public_id", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.CharField(source="user.email", read_only=True)

    class Meta:
        model = UserProfile
        extra_kwargs = {
            "url": {"lookup_field": "public_id"},
        }
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
    user = IdOrHyperlinkedRelatedField(
        source="user.profile",
        view_name="userprofile-detail",
        lookup_field="public_id",
        queryset=UserProfile.objects.all(),
    )

    class Meta:
        model = Seat
        extra_kwargs = {
            "url": {"lookup_field": "public_id"},
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

    def validate(self, attrs):
        if user := attrs.pop("created_by", None):
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

    def create(self, validated_data):
        profile = validated_data.pop("user", None)
        if profile is not None:
            validated_data["user"] = profile.user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        profile = validated_data.pop("user", None)
        if profile is not None:
            validated_data["user"] = profile.user
        return super().update(instance, validated_data)


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
