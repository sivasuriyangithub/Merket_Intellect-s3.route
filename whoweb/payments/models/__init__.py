from django.dispatch import receiver
from djstripe.models import Plan, Event
from djstripe.signals import WEBHOOK_SIGNALS

from .billing_accounts import (
    MultiPlanCustomer,
    MultiPlanSubscription,
    BillingAccount,
    BillingAccountMember,
    BillingAccountOwner,
    record_transaction_consume_credits,
    record_transaction_expire_credits,
    record_transaction_refund_credits,
    record_transaction_sold_credits,
)
from .plans import WKPlan, WKPlanPreset

__all__ = [
    "MultiPlanCustomer",
    "MultiPlanSubscription",
    "BillingAccount",
    "BillingAccountMember",
    "BillingAccountOwner",
    "record_transaction_consume_credits",
    "record_transaction_expire_credits",
    "record_transaction_refund_credits",
    "record_transaction_sold_credits",
    "WKPlan",
    "WKPlanPreset",
]


def patched_get_or_create(cls, **kwargs):
    """ Get or create a Plan."""

    try:
        return Plan.objects.get(id=kwargs.get("id")), False
    except Plan.DoesNotExist:
        return cls.create(**kwargs), True


Plan.get_or_create = classmethod(patched_get_or_create)


def patched_create(cls, description=None, name=None, aggregate_usage=None, **kwargs):
    if aggregate_usage:
        kwargs["aggregate_usage"] = aggregate_usage
    return Plan._original_create(**kwargs)


Plan._original_create = Plan.create
Plan.create = classmethod(patched_create)


@receiver(WEBHOOK_SIGNALS["invoice.payment_succeeded"], sender=Event)
def on_payment_succeed_replenish_customer_credits(event: Event, **kwargs):
    acct: BillingAccount = event.customer.subscriber
    for item in event.customer.subscription.items:
        if item.plan.product.metadata.get("product") == "credits":
            acct.replenish_credits(amount=item.plan.quantity, evidence=(event,))
