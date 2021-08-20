import graphene
from graphene_django import DjangoObjectType

from .ledgers import account_code_to_short_name
from .models import LedgerEntry, Ledger, TransactionRelatedObject


class LedgerObjectType(DjangoObjectType):
    short_code = graphene.String()

    class Meta:
        model = Ledger
        fields = ("short_code", "liability", "name", "account_code")

    def resolve_shortcode(self: Ledger, info):
        return account_code_to_short_name[self.account_code]


class LedgerEntryObjectType(DjangoObjectType):
    ledger = graphene.Field(LedgerObjectType)

    class Meta:
        model = LedgerEntry
        fields = ("ledger", "amount")
        read_only_fields = fields


class TransactionObjectType(DjangoObjectType):
    entries = graphene.List(
        LedgerEntryObjectType, resolver=lambda s, i: s.transaction.entries.all()
    )
    transaction_id = graphene.String(resolver=lambda s, i: s.transaction.transaction_id)
    kind = graphene.String(resolver=lambda s, i: s.transaction.kind)
    notes = graphene.String(resolver=lambda s, i: s.transaction.notes)
    posted_timestamp = graphene.DateTime(
        resolver=lambda s, i: s.transaction.posted_timestamp
    )

    class Meta:
        model = TransactionRelatedObject
        fields = ("entries", "transaction_id", "kind", "posted_timestamp", "notes")
