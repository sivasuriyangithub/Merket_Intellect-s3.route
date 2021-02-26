from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework_guardian.serializers import ObjectPermissionsAssignmentMixin
from rest_framework_simplejwt.serializers import TokenObtainSlidingSerializer

from whoweb.contrib.graphene_django.fields import NodeRelatedField
from whoweb.contrib.rest_framework.fields import IdOrHyperlinkedRelatedField
from whoweb.contrib.rest_framework.serializers import IdOrHyperlinkedModelSerializer
from .models import Seat, DeveloperKey, Group, UserProfile, User


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
            validated_data["user"] = profile["profile"].user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        profile = validated_data.pop("user", None)
        if profile is not None:
            validated_data["user"] = profile["profile"].user
        return super().update(instance, validated_data)


class DeveloperKeySerializer(
    ObjectPermissionsAssignmentMixin, IdOrHyperlinkedModelSerializer
):
    created_by = serializers.HiddenField(default=serializers.CurrentUserDefault())
    id = serializers.CharField(source="pk", read_only=True)
    graph_id = NodeRelatedField("DeveloperKeyNode", source="pk")
    network = IdOrHyperlinkedRelatedField(
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
        if not user.has_perm("add_developerkeys", attrs["network"]):
            raise PermissionDenied
        return attrs

    def get_permissions_map(self, created):
        authGroup = self.instance.group.credentials_admin_authgroup
        return {"delete_developerkey": [authGroup], "view_developerkey": [authGroup]}


class ImpersonatedTokenObtainSlidingSerializer(TokenObtainSlidingSerializer):

    xperweb_id = serializers.CharField(required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        del self.fields[self.username_field]
        del self.fields["password"]

    def validate(self, attrs):
        self.user = get_object_or_404(
            User,
            Q(profile__xperweb_id=attrs["xperweb_id"])
            | Q(username=attrs["xperweb_id"]),
        )
        token = self.get_token(self.user)

        return {"token": str(token)}


class AuthManagementSerializer(serializers.Serializer):
    seat = IdOrHyperlinkedRelatedField(
        view_name="seat-detail",
        lookup_field="public_id",
        queryset=Seat.objects.all(),
        required=False,
    )

    password = serializers.CharField(required=True, write_only=True)
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
