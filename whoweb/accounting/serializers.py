from rest_framework import serializers

from .models import Transaction, LedgerEntry, Ledger
from .ledgers import account_code_to_short_name


class LedgerSerializer(serializers.ModelSerializer):
    shortcode = serializers.SerializerMethodField()

    class Meta:
        model = Ledger
        fields = ("shortcode", "liability", "name", "account_code")
        read_only_fields = fields

    def get_shortcode(self, obj):
        return account_code_to_short_name[obj.account_code]


class LedgerEntrySerializer(serializers.ModelSerializer):
    ledger = LedgerSerializer()

    class Meta:
        model = LedgerEntry
        fields = ("ledger", "amount")
        read_only_fields = fields


class TransactionSerializer(serializers.ModelSerializer):
    entries = LedgerEntrySerializer(many=True, read_only=True)

    class Meta:
        model = Transaction
        fields = ("notes", "kind", "created_by", "posted_timestamp", "entries")
        read_only_fields = fields
