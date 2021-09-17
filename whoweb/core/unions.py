import graphene

from whoweb.payments.schema import BillingAccountMemberNode, BillingAccountNode
from whoweb.search.schema import SearchExportNode, DerivationStoreNode


class EvidenceObjectType(graphene.Union):
    class Meta:
        types = (
            SearchExportNode,
            BillingAccountMemberNode,
            BillingAccountNode,
            DerivationStoreNode,
        )
