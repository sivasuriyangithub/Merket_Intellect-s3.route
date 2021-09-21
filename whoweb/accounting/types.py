import django_filters
import graphene
from django_filters import FilterSet
from graphene import relay
from graphene_django import DjangoObjectType
from graphene_django.registry import get_global_registry

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


class TransactionObjectTypeFilterSet(FilterSet):
    ledger_code = django_filters.NumberFilter(
        field_name="transaction__entries__ledger__account_code"
    )
    posted_timestamp = django_filters.DateRangeFilter(field_name="published",)
    posted_after = django_filters.DateFilter(
        field_name="posted_timestamp", lookup_expr="gt"
    )
    posted_before = django_filters.DateFilter(
        field_name="posted_timestamp", lookup_expr="lt"
    )


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
    related_objects = graphene.List("whoweb.core.unions.EvidenceObjectType")

    class Meta:
        model = TransactionRelatedObject
        filterset_class = TransactionObjectTypeFilterSet
        fields = ("entries", "transaction_id", "kind", "posted_timestamp", "notes")
        interfaces = (relay.Node,)

    def resolve_related_objects(self: TransactionRelatedObject, info):
        return [tro.related_object for tro in self.transaction.related_objects.all()]
        # for obj in all_evidences:
        #     graph_type = registry.get_type_for_model(obj)
        #     global_id = to_global_id
