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
        extra_kwargs = {
            "url": {"lookup_field": "uuid"},
        }
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
        from whoweb.users.models import Group

        if not validated_data["uploadable"]:
            group_id = validated_data["group_id"]
            group_name = validated_data.get("group_name") or group_id
            xperweb_id = validated_data["xperweb_id"]
            email = validated_data["email"]
            profile, _ = UserProfile.get_or_create(username=xperweb_id, email=email)
            group, _ = Group.objects.get_or_create(
                name=group_name, slug=slugify(group_id)
            )
            seat, _ = group.get_or_add_user(
                user=profile.user, display_name=profile.user.get_full_name()
            )
            plan, _ = WKPlan.objects.get_or_create(
                credits_per_enrich=validated_data["credits_per_enrich"],
                credits_per_work_email=validated_data["credits_per_work_email"],
                credits_per_personal_email=validated_data["credits_per_personal_email"],
                credits_per_phone=validated_data["credits_per_phone"],
            )
            if group_id == "public":
                billing_account_name = f"{xperweb_id} Primary Billing Account"
            else:
                billing_account_name = f"{group_name} Primary Billing Account"
            billing_account, _ = BillingAccount.objects.update_or_create(
                name=billing_account_name,
                slug=slugify(billing_account_name),
                group=group,
                defaults=dict(plan=plan),
            )
            billing_member, _ = billing_account.get_or_add_user(
                user=profile.user, seat=seat
            )
            billing_member.seat_credits = validated_data["seat_credits"]
            billing_member.save()
        else:
            seat = None
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
