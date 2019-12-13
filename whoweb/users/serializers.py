from rest_framework import serializers

from .models import Seat, OrganizationCredentials


class SeatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Seat
        fields = ["user_id"]


class OrganizationCredentialsSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationCredentials
        fields = ["pk", "seat", "group", "api_key", "secret", "test_key"]
        read_only_fields = ["pk", "api_key", "secret"]
