from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from whoweb.accounting.serializers import TransactionSerializer
from whoweb.contrib.rest_framework.fields import (
    MultipleChoiceListField,
    PublicPrivateMultipleChoiceListField,
    IdOrHyperlinkedRelatedField,
)
from whoweb.contrib.rest_framework.serializers import IdOrHyperlinkedModelSerializer
from whoweb.search.models import (
    SearchExport,
    FilteredSearchQuery,
    FilteredSearchFilters,
    ExportOptions,
    FilteredSearchFilterElement,
    ResultProfile,
)
from whoweb.search.models.profile import WORK, PERSONAL, SOCIAL, PROFILE, PHONE
from whoweb.users.models import Seat


class ExportOptionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExportOptions
        fields = ("webhooks", "format", "title", "metadata")

    def to_representation(self, instance):
        return instance.serialize()


class FilteredSearchFilterElementSerializer(serializers.ModelSerializer):
    value = serializers.JSONField(style={"base_template": "input.html"})

    class Meta:
        model = FilteredSearchFilterElement
        fields = ("field", "value", "truth")

    def to_representation(self, instance):
        return instance.serialize()


class FilteredSearchFiltersSerializer(serializers.ModelSerializer):
    required = FilteredSearchFilterElementSerializer(many=True, default=list)
    desired = FilteredSearchFilterElementSerializer(many=True, default=list)

    class Meta:
        model = FilteredSearchFilters
        fields = "__all__"

    def to_representation(self, instance):
        return instance.serialize()


class FilteredSearchQuerySerializer(serializers.ModelSerializer):
    filters = FilteredSearchFiltersSerializer()
    export = ExportOptionsSerializer(required=False)
    defer = PublicPrivateMultipleChoiceListField(
        public_choices=FilteredSearchQuery.PUBLIC_DEFER_CHOICES,
        choices=FilteredSearchQuery.DEFER_CHOICES,
        required=False,
        default=list,
    )
    contact_filters = MultipleChoiceListField(
        choices=FilteredSearchQuery.CONTACT_FILTER_CHOICES, required=False, default=list
    )

    class Meta:
        model = FilteredSearchQuery
        fields = "__all__"

    def to_representation(self, instance):
        return instance.serialize()


class SearchExportSerializer(IdOrHyperlinkedModelSerializer):
    query = FilteredSearchQuerySerializer()
    results_url = serializers.HyperlinkedRelatedField(
        view_name="exportresult-detail", read_only=True, source="uuid",
    )
    status_name = serializers.SerializerMethodField()
    for_campaign = serializers.BooleanField(source="uploadable", required=False)
    transactions = TransactionSerializer(many=True, read_only=True)
    seat = IdOrHyperlinkedRelatedField(
        view_name="seat-detail",
        lookup_field="public_id",
        queryset=Seat.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = SearchExport
        extra_kwargs = {"url": {"lookup_field": "uuid"}}
        depth = 1
        read_only_fields = [
            "status",
            "status_name",
            "status_changed",
            "progress_counter",
            "valid_count",
            "charge",
            "charged",
            "target",
            "with_invites",
            "results_url",
            "transactions",
        ]
        fields = [
            "url",
            "results_url",
            "uuid",
            "seat",
            "query",
            "status_name",
            "status_changed",
            "sent",
            "sent_at",
            "progress_counter",
            "target",
            "notify",
            "charge",
            "for_campaign",
            "on_trial",
            "charged",
            "transactions",
        ]

    def get_status_name(self, obj):
        return SearchExport.STATUS[int(obj.status)]

    def create(self, validated_data):
        export = SearchExport.create_from_query(
            seat=validated_data["seat"],
            query=validated_data["query"],
            uploadable=validated_data["uploadable"],
            notify=not validated_data["uploadable"],
            charge=not validated_data["uploadable"],
        )
        return export


class SearchExportDataSerializer(serializers.Serializer):
    _id = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    email = serializers.EmailField()
    graded_emails = serializers.JSONField()
    emails = serializers.ListField(serializers.EmailField())
    grade = serializers.CharField()
    derivation_status = serializers.CharField()


class ResultProfileSerializer(serializers.Serializer):
    id = serializers.CharField(source="_id")
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    company = serializers.CharField()
    timeout = serializers.IntegerField(
        required=False, initial=28, default=28, write_only=True
    )
    filters = serializers.MultipleChoiceField(
        choices=[WORK, SOCIAL, PERSONAL, PROFILE, PHONE],
        initial=[WORK, SOCIAL, PERSONAL, PROFILE],
        default=[WORK, SOCIAL, PERSONAL, PROFILE],
        write_only=True,
    )
    title = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)
    graded_emails = serializers.JSONField(read_only=True)
    emails = serializers.ListField(
        child=serializers.EmailField(read_only=True), read_only=True
    )
    grade = serializers.CharField(read_only=True)
    graded_phones = serializers.JSONField(read_only=True)
    social_links = serializers.JSONField(read_only=True)
    li_url = serializers.CharField(read_only=True)
    twitter = serializers.CharField(read_only=True)
    facebook = serializers.CharField(read_only=True)
    status = serializers.CharField(source="derivation_status", read_only=True)

    class Meta:
        read_only_fields = ("emails",)

    def create(self, validated_data):
        filters = validated_data["filters"]
        timeout = validated_data["timeout"]
        profile = ResultProfile.from_json(validated_data)
        profile.derive_contact(filters=filters, timeout=timeout)
        return profile.to_json()
