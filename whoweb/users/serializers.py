from rest_framework import serializers
from rest_framework.exceptions import ValidationError, PermissionDenied

from .models import Seat, OrganizationCredentials, Group


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Group
        fields = ("name", "slug", "pk")
        read_only_fields = fields


class SeatSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Seat
        fields = ("name", "group", "pk")
        read_only_fields = fields


class OrganizationCredentialsSerializer(serializers.HyperlinkedModelSerializer):
    created_by = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = OrganizationCredentials
        fields = ["pk", "seat", "group", "api_key", "secret", "test_key", "created_by"]
        read_only_fields = ["pk", "api_key", "secret"]

    def validate(self, attrs):
        if not attrs["created_by"].has_perm(
            "add_organizationcredentials", attrs["group"]
        ):
            raise PermissionDenied
        if attrs["seat"] and attrs["seat"].organization != attrs["group"]:
            raise ValidationError("Seat must be a member of the group.")
        return attrs
