import graphene
from graphene_django.filter import DjangoFilterConnectionField

from whoweb.contrib.graphene_django.types import GuardedObjectType, ObscureIdNode
from whoweb.contrib.rest_framework.filters import ObjectPermissionsFilter
from whoweb.contrib.rest_framework.permissions import (
    IsSuperUser,
    ObjectPermissions,
)
from whoweb.users.schema import NetworkNode
from .models import WKPlan, BillingAccount, BillingAccountMember


class PlanNode(GuardedObjectType):
    class Meta:
        model = WKPlan
        interfaces = (ObscureIdNode,)
        filter_fields = []
        permission_classes = [IsSuperUser | ObjectPermissions]
        filter_backends = (ObjectPermissionsFilter,)
        fields = (
            "credits_per_enrich",
            "credits_per_work_email",
            "credits_per_personal_email",
            "credits_per_phone",
        )


class BillingAccountNode(GuardedObjectType):
    network = graphene.Field(NetworkNode)

    class Meta:
        model = BillingAccount
        interfaces = (ObscureIdNode,)
        filter_fields = []
        permission_classes = [IsSuperUser | ObjectPermissions]
        filter_backends = (ObjectPermissionsFilter,)
        fields = ("seats", "plan", "credit_pool")


class BillingAccountMemberNode(GuardedObjectType):
    billing_account = graphene.Field(BillingAccountNode, source="organization")

    class Meta:
        model = BillingAccountMember
        interfaces = (ObscureIdNode,)
        filter_fields = []
        permission_classes = [IsSuperUser | ObjectPermissions]
        filter_backends = (ObjectPermissionsFilter,)
        fields = (
            "seat",
            "seat_credits",
            "pool_credits",
        )


class Query(graphene.ObjectType):
    plans = DjangoFilterConnectionField(PlanNode)
    billing_accounts = DjangoFilterConnectionField(BillingAccountNode)
    billing_account_members = DjangoFilterConnectionField(BillingAccountMemberNode)
