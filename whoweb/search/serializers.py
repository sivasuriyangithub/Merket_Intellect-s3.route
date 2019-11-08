from rest_framework import serializers
from slugify import slugify

from whoweb.payments.models import BillingAccount
from whoweb.search.models import (
    SearchExport,
    FilteredSearchQuery,
    FilteredSearchFilters,
    ExportOptions,
    FilteredSearchFilterElement,
)
from whoweb.users.models import UserProfile


class ExportOptionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExportOptions
        fields = "__all__"

    def to_representation(self, instance):
        return instance.serialize()


class FilteredSearchFilterElementSerializer(serializers.ModelSerializer):
    class Meta:
        model = FilteredSearchFilterElement
        fields = "__all__"

    def to_representation(self, instance):
        return instance.serialize()


class FilteredSearchFiltersSerializer(serializers.ModelSerializer):
    required = serializers.ListField(FilteredSearchFilterElementSerializer)
    desired = serializers.ListField(FilteredSearchFilterElementSerializer)

    class Meta:
        model = FilteredSearchFilters
        fields = "__all__"

    def to_representation(self, instance):
        return instance.serialize()


class FilteredSearchQuerySerializer(serializers.ModelSerializer):
    filters = FilteredSearchFiltersSerializer()
    export = ExportOptionsSerializer(required=False)

    class Meta:
        model = FilteredSearchQuery
        fields = "__all__"

    def to_representation(self, instance):
        return instance.serialize()


class SearchExportSerializer(serializers.ModelSerializer):
    query = FilteredSearchQuerySerializer()
    status_name = serializers.SerializerMethodField()
    xperweb_id = serializers.CharField(write_only=True)
    group_name = serializers.CharField(write_only=True)
    group_id = serializers.CharField(allow_blank=True, write_only=True)
    email = serializers.EmailField(write_only=True)
    seat_credits = serializers.IntegerField(write_only=True)
    for_campaign = serializers.BooleanField(source="uploadable", required=False)

    class Meta:
        model = SearchExport
        depth = 1
        fields = [
            "id",
            "uuid",
            "seat",
            "query",
            "status_name",
            "status",
            "status_changed",
            "sent",
            "sent_at",
            "progress_counter",
            "target",
            "charged",
            "refunded",
            "valid_count",
            "notify",
            "charge",
            "for_campaign",
            "on_trial",
            "xperweb_id",
            "group_name",
            "group_id",
            "email",
            "seat_credits",
        ]

    def get_status_name(self, obj):
        return SearchExport.STATUS[int(obj.status)]

    def create(request, validated_data):
        from whoweb.users.models import Group

        group_name = validated_data["group_name"]
        group_id = validated_data.get("group_id", group_name)
        billing_account_name = f"{group_name} Primary Billing Account"
        xperweb_id = validated_data["xperweb_id"]
        email = validated_data["email"]
        profile, _ = UserProfile.get_or_create(username=xperweb_id, email=email)
        group, _ = Group.objects.get_or_create(name=group_name, slug=slugify(group_id))
        seat, _ = group.get_or_add_user(
            user=profile.user, display_name=profile.user.get_full_name()
        )
        billing_account, _ = BillingAccount.objects.get_or_create(
            name=billing_account_name, slug=slugify(billing_account_name), group=group
        )
        billing_member, _ = billing_account.get_or_add_user(
            user=profile.user, seat=seat, seat_credits=validated_data["seat_credits"]
        )
        export = SearchExport.create_from_query(
            seat=seat,
            query=validated_data["query"],
            uploadable=validated_data["uploadable"],
        )
        return export
