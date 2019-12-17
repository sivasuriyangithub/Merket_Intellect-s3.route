from abc import ABCMeta
from typing import Type

from django.contrib.auth import get_user_model
from graphene import relay
from graphene.relay.node import AbstractNode
from graphql_relay import to_global_id
from rest_framework import serializers
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework_guardian.serializers import ObjectPermissionsAssignmentMixin

from users.schema import UserNode
from .models import Seat, OrganizationCredentials, Group

User = get_user_model()


class NodeRelatedField(serializers.RelatedField):
    """
    A read only field that represents its targets using their
    plain string representation.
    """

    def __init__(self, node: str, **kwargs):
        kwargs["read_only"] = True
        self.node = node
        super().__init__(**kwargs)

    def to_representation(self, value):
        return to_global_id(self.node, value)


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
    id = serializers.CharField(source="pk")

    class Meta:
        model = Seat
        fields = ("display_name", "network", "created_by", "url", "id")

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ["network", "user"]
        else:
            return []

    def validate(self, attrs):
        user = attrs["created_by"]
        if not user.has_perm("add_seat", attrs["group"]):
            raise PermissionDenied
        return attrs

    def get_permissions_map(self, created):
        admin_group = self.instance.group.seat_admin_authgroup
        seat_viewers = self.instance.group.seat_viewers
        user = self.instance.user
        return {
            "view_seat": [admin_group, seat_viewers, user],
            "change_seat": [admin_group, user],
            "delete_seat": [admin_group],
        }


class OrganizationCredentialsSerializer(
    ObjectPermissionsAssignmentMixin, serializers.HyperlinkedModelSerializer
):
    created_by = serializers.HiddenField(default=serializers.CurrentUserDefault())
    id = serializers.CharField()

    class Meta:
        model = OrganizationCredentials
        fields = ["id", "group", "api_key", "secret", "test_key", "created_by", "url"]
        read_only_fields = ["id", "api_key", "secret"]

    def validate(self, attrs):
        user = attrs["created_by"]
        if not user.has_perm("add_organizationcredentials", attrs["group"]):
            raise PermissionDenied
        return attrs

    def get_permissions_map(self, created):
        authGroup = self.instance.group.credentials_admin_authgroup
        return {
            "delete_organizationcredentials": [authGroup],
            "view_organizationcredentials": [authGroup],
        }
