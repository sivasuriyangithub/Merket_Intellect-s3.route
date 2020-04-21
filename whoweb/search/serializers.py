from django.http import Http404
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from whoweb.accounting.serializers import TransactionSerializer
from whoweb.contrib.rest_framework.fields import (
    MultipleChoiceListField,
    PublicPrivateMultipleChoiceListField,
    IdOrHyperlinkedRelatedField,
)
from whoweb.contrib.rest_framework.serializers import IdOrHyperlinkedModelSerializer
from whoweb.core.router import router
from whoweb.payments.exceptions import PaymentRequired, SubscriptionError
from whoweb.payments.models import BillingAccountMember
from whoweb.search.models import (
    SearchExport,
    FilteredSearchQuery,
    FilteredSearchFilters,
    ExportOptions,
    FilteredSearchFilterElement,
    ResultProfile,
    DerivationCache,
)
from whoweb.search.models.profile import (
    WORK,
    PERSONAL,
    SOCIAL,
    PROFILE,
    PHONE,
    BatchProfileActionResult,
)


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
    billing_seat = IdOrHyperlinkedRelatedField(
        view_name="billingaccountmember-detail",
        lookup_field="public_id",
        queryset=BillingAccountMember.objects.all(),
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
            "billing_seat",
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

    def validate(self, attrs):
        billing_seat = attrs["billing_seat"]
        if not (
            billing_seat.plan
            or billing_seat.organization.customer().has_any_active_subscription()
        ):
            raise PaymentRequired()
        return attrs

    def create(self, validated_data):
        try:
            return SearchExport.create_from_query(
                billing_seat=validated_data["billing_seat"],
                query=validated_data["query"],
                uploadable=validated_data["uploadable"],
                notify=not validated_data["uploadable"],
                charge=not validated_data["uploadable"],
            )
        except SubscriptionError as e:
            raise PaymentRequired(detail=e)


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
    id = serializers.CharField(source="_id", allow_null=True)
    relevance_score = serializers.CharField(allow_null=True)
    first_name = serializers.CharField(allow_null=True)
    last_name = serializers.CharField(allow_null=True)
    company = serializers.CharField(allow_null=True)
    title = serializers.CharField(allow_null=True)
    business_function = serializers.CharField(allow_null=True)
    seniority_level = serializers.CharField(allow_null=True)
    industry = serializers.CharField(allow_null=True)
    picture_url = serializers.CharField(allow_null=True)
    city = serializers.CharField(allow_null=True)
    state = serializers.CharField(allow_null=True)
    country = serializers.CharField(allow_null=True)
    geo_loc = serializers.JSONField(allow_null=True)
    email = serializers.EmailField(allow_null=True)
    grade = serializers.CharField(allow_null=True)
    emails = serializers.ListField(child=serializers.EmailField(), allow_null=True)
    graded_emails = serializers.JSONField(allow_null=True)
    graded_phones = serializers.JSONField(allow_null=True)
    social_links = serializers.JSONField(allow_null=True)
    li_url = serializers.CharField(allow_null=True)
    twitter = serializers.CharField(allow_null=True)
    facebook = serializers.CharField(allow_null=True)
    current_experience = serializers.JSONField(allow_null=True)
    experience = serializers.JSONField(allow_null=True)
    education_history = serializers.JSONField(allow_null=True)
    diversity = serializers.JSONField(allow_null=True)
    total_experience = serializers.IntegerField(allow_null=True)
    time_at_current_company = serializers.IntegerField(allow_null=True)
    time_at_current_position = serializers.IntegerField(allow_null=True)
    skills = serializers.JSONField(allow_null=True)
    attenuated_skills = serializers.JSONField(allow_null=True)

    status = serializers.CharField(source="derivation_status", allow_null=True)


class BatchResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = BatchProfileActionResult
        fields = ("id", "size", "status_url")
        read_only_fields = fields


class DeriveContactSerializer(serializers.Serializer):
    initiated_by = serializers.HiddenField(default=serializers.CurrentUserDefault())
    billing_seat = IdOrHyperlinkedRelatedField(
        view_name="billingaccountmember-detail",
        lookup_field="public_id",
        queryset=BillingAccountMember.objects.all(),
        required=False,
        allow_null=True,
    )
    id = serializers.CharField(source="_id", write_only=True, required=False)
    first_name = serializers.CharField(required=False, write_only=True)
    last_name = serializers.CharField(required=False, write_only=True)
    company = serializers.CharField(required=False, write_only=True)
    timeout = serializers.IntegerField(
        required=False, initial=28, default=28, write_only=True
    )
    filters = serializers.MultipleChoiceField(
        choices=[WORK, SOCIAL, PERSONAL, PROFILE, PHONE],
        initial=[WORK, SOCIAL, PERSONAL, PROFILE],
        default=[WORK, SOCIAL, PERSONAL, PROFILE],
        write_only=True,
    )
    credits_used = serializers.IntegerField(read_only=True)
    credits_remaining = serializers.IntegerField(read_only=True)
    profile = ResultProfileSerializer(read_only=True)

    class Meta:
        read_only_fields = ("emails", "profile")

    def validate(self, attrs):
        if not (
            "_id" in attrs
            or all(["first_name" in attrs, "last_name" in attrs, "company" in attrs])
        ):
            raise ValidationError(
                "Must provide an id or all of first_name, last_name, and company."
            )

        return attrs

    def create(self, validated_data):

        filters = validated_data.pop("filters")
        timeout = validated_data.pop("timeout")
        initiated_by = validated_data.pop("initiated_by")
        if not all(
            [
                "first_name" in validated_data,
                "last_name" in validated_data,
                "company" in validated_data,
            ]
        ):
            search = router.profile_lookup(json={"profile_id": validated_data["_id"]})
            results = search.get("results")
            if not results:
                raise Http404("Unable to find a profile matching the supplied id.")
            profile = ResultProfile(**results[0])
        else:
            profile = ResultProfile(**validated_data)
        profile.derive_contact(filters=filters, timeout=timeout)
        billing_seat = validated_data["billing_seat"]
        cache_obj, charge = DerivationCache.get_or_charge(
            billing_seat=billing_seat, profile=profile
        )
        if charge > 0:
            billing_seat.consume_credits(
                amount=charge, evidence=(cache_obj,), initiated_by=initiated_by
            )

        validated_data["profile"] = profile.dict()
        validated_data["credits_used"] = charge
        validated_data["credits_remaining"] = billing_seat.credits
        return validated_data


class DeriveContactBatchInputEntitySerializer(serializers.Serializer):
    id = serializers.CharField(write_only=True)
    first_name = serializers.CharField(required=False, write_only=True)
    last_name = serializers.CharField(required=False, write_only=True)
    company = serializers.CharField(required=False, write_only=True)
    filters = serializers.MultipleChoiceField(
        choices=[WORK, SOCIAL, PERSONAL, PROFILE, PHONE],
        initial=[WORK, SOCIAL, PERSONAL, PROFILE],
        default=[WORK, SOCIAL, PERSONAL, PROFILE],
        write_only=True,
    )

    def validate(self, attrs):
        if not (
            "_id" in attrs
            or all(["first_name" in attrs, "last_name" in attrs, "company" in attrs])
        ):
            raise ValidationError(
                "Must provide an id or all of first_name, last_name, and company."
            )

        return attrs


class BatchDeriveContactSerializer(serializers.Serializer):
    initiated_by = serializers.HiddenField(default=serializers.CurrentUserDefault())
    billing_seat = IdOrHyperlinkedRelatedField(
        view_name="billingaccountmember-detail",
        lookup_field="public_id",
        queryset=BillingAccountMember.objects.all(),
    )
    input = DeriveContactBatchInputEntitySerializer(many=True)
    webhooks = serializers.ListSerializer(child=serializers.URLField())
    batch = BatchResultSerializer()

    class Meta:
        depth = 1


class ProfileEnrichmentSerializer(serializers.Serializer):
    initiated_by = serializers.HiddenField(default=serializers.CurrentUserDefault())
    billing_seat = IdOrHyperlinkedRelatedField(
        view_name="billingaccountmember-detail",
        lookup_field="public_id",
        queryset=BillingAccountMember.objects.all(),
    )
    email = serializers.EmailField(allow_null=True, required=False)
    user_id = serializers.CharField(allow_null=True, required=False)
    linkedin_url = serializers.URLField(allow_null=True, required=False)
    profile_id = serializers.CharField(allow_null=True, required=False)
    get_web_profile = serializers.NullBooleanField(required=False)
    no_cache = serializers.NullBooleanField(required=False)
    min_confidence = serializers.FloatField(allow_null=True, required=False)

    profile = ResultProfileSerializer(read_only=True)
    status = serializers.CharField(read_only=True)

    def create(self, validated_data):
        initiated_by = validated_data.pop("initiated_by")
        billing_seat = validated_data.pop("billing_seat")

        linkedin_url = validated_data.get("linkedin_url")
        if linkedin_url and linkedin_url.endswith("/"):
            validated_data["linkedin_url"] = linkedin_url[:-1]
        profile = ResultProfile.enrich(**validated_data)

        charge = billing_seat.plan.credits_per_enrich
        if charge > 0:
            billing_seat.consume_credits(
                amount=charge, evidence=(), initiated_by=initiated_by
            )

        validated_data["profile"] = profile.to_dict()
        validated_data["status"] = profile.returned_status
        validated_data["credits_used"] = charge
        validated_data["credits_remaining"] = billing_seat.credits


class ProfileEnrichmentBatchInputEntitySerializer(serializers.Serializer):
    email = serializers.EmailField(allow_null=True, required=False)
    user_id = serializers.CharField(allow_null=True, required=False)
    linkedin_url = serializers.URLField(allow_null=True, required=False)
    profile_id = serializers.CharField(allow_null=True, required=False)
    get_web_profile = serializers.NullBooleanField(required=False)
    no_cache = serializers.NullBooleanField(required=False)
    min_confidence = serializers.FloatField(allow_null=True, required=False)

    def validate(self, attrs):
        linkedin_url = attrs.get("linkedin_url")
        if linkedin_url and linkedin_url.endswith("/"):
            attrs["linkedin_url"] = linkedin_url[:-1]
        return attrs


class BatchProfileEnrichmentSerializer(serializers.Serializer):
    initiated_by = serializers.HiddenField(default=serializers.CurrentUserDefault())
    billing_seat = IdOrHyperlinkedRelatedField(
        view_name="billingaccountmember-detail",
        lookup_field="public_id",
        queryset=BillingAccountMember.objects.all(),
    )
    input = ProfileEnrichmentBatchInputEntitySerializer(many=True)
    webhooks = serializers.ListSerializer(child=serializers.URLField())
    batch = BatchResultSerializer()

    class Meta:
        depth = 1
