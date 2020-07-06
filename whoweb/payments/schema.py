import graphene
from djstripe.models import SubscriptionItem, Plan, Product
from graphene_django.filter import DjangoFilterConnectionField

from whoweb.contrib.graphene_django.types import GuardedObjectType, ObscureIdNode
from whoweb.contrib.rest_framework.filters import ObjectPermissionsFilter
from whoweb.contrib.rest_framework.permissions import (
    IsSuperUser,
    ObjectPermissions,
)
from whoweb.users.schema import NetworkNode
from .models import WKPlan, BillingAccount, BillingAccountMember, MultiPlanSubscription
from .permissions import BillingAccountMemberPermissionsFilter


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


class StripeProductMetadata(graphene.ObjectType):
    product = graphene.String()
    is_addon = graphene.Boolean()


class StripeProductObjectType(GuardedObjectType):
    metadata = graphene.Field(StripeProductMetadata)

    class Meta:
        model = Product
        fields = ["id", "name", "metadata", "unit_label"]


class StripePlanTiersObjectType(graphene.ObjectType):
    up_to = graphene.Int()
    flat_amount = graphene.Int()
    unit_amount = graphene.Int()


class StripePlanObjectType(GuardedObjectType):
    product = graphene.Field(StripeProductObjectType)
    tiers = graphene.List(StripePlanTiersObjectType)

    class Meta:
        model = Plan
        fields = [
            "id",
            "amount",
            "currency",
            "interval",
            "interval_count",
            "product",
            "metadata",
            "tiers",
            "trial_period_days",
            "statement_descriptor",
        ]


class SubscriptionItemObjectType(GuardedObjectType):
    plan = graphene.Field(StripePlanObjectType)

    class Meta:
        model = SubscriptionItem
        fields = [
            "created",
            "plan",
            "quantity",
            "metadata",
            "description",
        ]


class SubscriptionObjectType(GuardedObjectType):
    items = graphene.List(
        SubscriptionItemObjectType, resolver=lambda s, i: s.items.all()
    )
    can_charge = graphene.Boolean()
    is_valid = graphene.Boolean()
    status = graphene.String(source="get_status_display")

    class Meta:
        model = MultiPlanSubscription
        fields = [
            "created",
            "description",
            "metadata",
            "billing_cycle_anchor",
            "cancel_at_period_end",
            "canceled_at",
            "collection_method",
            "current_period_end",
            "current_period_start",
            "days_until_due",
            "ended_at",
            "plan",
            "quantity",
            "start",
            "status",
            "tax_percent",
            "trial_end",
            "trial_start",
            "items",
            "is_valid",
        ]

    def resolve_can_charge(self, info):
        return self.customer.can_charge()


class BillingAccountNode(GuardedObjectType):
    network = graphene.Field(NetworkNode)
    subscription = graphene.Field(SubscriptionObjectType)
    rest_id = graphene.ID(source="public_id")

    class Meta:
        model = BillingAccount
        interfaces = (ObscureIdNode,)
        filter_fields = []
        permission_classes = [IsSuperUser | ObjectPermissions]
        filter_backends = (ObjectPermissionsFilter,)
        fields = ("seats", "plan", "credit_pool", "customer_type")


class BillingAccountMemberNode(GuardedObjectType):
    billing_account = graphene.Field(BillingAccountNode, source="organization")
    credits = graphene.Int()
    rest_id = graphene.ID(source="public_id")

    class Meta:
        model = BillingAccountMember
        interfaces = (ObscureIdNode,)
        filter_fields = []
        permission_classes = [IsSuperUser | ObjectPermissions]
        filter_backends = (
            ObjectPermissionsFilter | BillingAccountMemberPermissionsFilter,
        )
        fields = ("seat", "pool_credits")


class Query(graphene.ObjectType):
    plans = DjangoFilterConnectionField(PlanNode)
    billing_accounts = DjangoFilterConnectionField(BillingAccountNode)
    billing_account_members = DjangoFilterConnectionField(BillingAccountMemberNode)
