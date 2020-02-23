from rest_framework import serializers
from slugify import slugify

from whoweb.contrib.rest_framework.serializers import IdOrHyperlinkedModelSerializer
from whoweb.users.models import Seat
from whoweb.accounting.serializers import TransactionSerializer
from whoweb.contrib.rest_framework.fields import (
    MultipleChoiceListField,
    PublicPrivateMultipleChoiceListField,
    IdOrHyperlinkedRelatedField,
)
from whoweb.payments.models import BillingAccount, WKPlan
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
