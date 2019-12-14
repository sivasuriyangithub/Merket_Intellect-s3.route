from rest_framework import serializers
from rest_framework.exceptions import ValidationError, PermissionDenied

from .models import Seat, OrganizationCredentials, Group


class SeatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Seat
        fields = ["user_id"]


class SeatForeignKey(serializers.PrimaryKeyRelatedField):
    def get_queryset(self):
        return


class OrganizationCredentialsSerializer(serializers.ModelSerializer):
    current_user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = OrganizationCredentials
        fields = [
            "pk",
            "seat",
            "group",
            "api_key",
            "secret",
            "test_key",
            "current_user",
        ]
        read_only_fields = ["pk", "api_key", "secret"]

    def validate(self, attrs):
        if not attrs["current_user"].has_perm(
            "add_organizationcredentials", attrs["group"]
        ):
            raise PermissionDenied
        if attrs["seat"] and attrs["seat"].organization != attrs["group"]:
            raise ValidationError("Seat must be a member of the group.")
        return attrs
