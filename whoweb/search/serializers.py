from rest_framework import serializers

from whoweb.search.models import SearchExport, FilteredSearchQuery


class FilteredSearchQuerySerializer(serializers.ModelSerializer):
    class Meta:
        model = FilteredSearchQuery
        fields = "__all__"

    def to_representation(self, instance):
        return instance.serialize()


class SearchExportSerializer(serializers.ModelSerializer):
    query = FilteredSearchQuerySerializer()

    class Meta:
        model = SearchExport
        fields = [
            "seat",
            "uuid",
            "query",
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
            "uploadable",
            "on_trial",
        ]
