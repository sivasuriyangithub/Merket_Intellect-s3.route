from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework_guardian.serializers import ObjectPermissionsAssignmentMixin

from whoweb.contrib.graphene_django.fields import NodeRelatedField
from .models import Seat, DeveloperKey, Group

User = get_user_model()


class UserSerializer(serializers.HyperlinkedModelSerializer):
    graph_id = NodeRelatedField("UserNode", source="pk")

    class Meta:
        model = User
        fields = ("username", "url", "graph_id", "email")
        read_only_fields = fields


class NetworkSerializer(serializers.HyperlinkedModelSerializer):
    graph_id = NodeRelatedField("NetworkNode", source="pk")
    id = serializers.CharField(source="pk")

    class Meta:
        model = Group
        fields = ("name", "slug", "url", "id", "graph_id")
        read_only_fields = fields


class SeatSerializer(
    ObjectPermissionsAssignmentMixin, serializers.HyperlinkedModelSerializer
):
    created_by = serializers.HiddenField(default=serializers.CurrentUserDefault())
    network = serializers.HyperlinkedRelatedField(
        source="organization", view_name="group-detail", queryset=Group.objects.all()
    )
    id = serializers.CharField(source="pk", read_only=True)
    graph_id = NodeRelatedField("SeatNode", source="pk")

    class Meta:
        model = Seat
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


class DeveloperKeySerializer(
    ObjectPermissionsAssignmentMixin, serializers.HyperlinkedModelSerializer
):
    created_by = serializers.HiddenField(default=serializers.CurrentUserDefault())
    id = serializers.CharField(source="pk", read_only=True)
    graph_id = NodeRelatedField("DeveloperKeyNode", source="pk")

    class Meta:
        model = DeveloperKey
        fields = [
            "id",
            "group",
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
