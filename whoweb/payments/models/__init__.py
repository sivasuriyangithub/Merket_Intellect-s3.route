import logging
from typing import Optional

from django.contrib.auth import get_user_model
from django.dispatch import receiver
from djstripe.exceptions import MultipleSubscriptionException
from djstripe.models import Plan, Event, SubscriptionItem, Account, Subscription
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

logger = logging.getLogger(__name__)

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
    "on_payment_succeed_replenish_customer_credits",
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


#
# def _attach_objects_post_save_hook(self, cls, data, pending_relations=None):
#     self._original_subscription_post_save_object_hook(
#         cls, data, pending_relations=pending_relations
#     )
#     MultiPlanSubscription.objects.get(pk=self.pk).sync_or_purge_subscription_items()
#
#
# _original_subscription_post_save_object_hook = (
#     Subscription._attach_objects_post_save_hook
# )
# Subscription._attach_objects_post_save_hook = _attach_objects_post_save_hook


# https://github.com/dj-stripe/dj-stripe/issues/830


def _account_manipulate_stripe_object_hook(cls, data):
    data["settings"]["branding"]["icon"] = None
    data["settings"]["branding"]["logo"] = None
    return _original_account_manipulate_stripe_object_hook(data)


_original_account_manipulate_stripe_object_hook = Account._manipulate_stripe_object_hook
Account._manipulate_stripe_object_hook = classmethod(
    _account_manipulate_stripe_object_hook
)


def get_stripe_webhook_user():
    User = get_user_model()
    stripe_webhook_user, created = User.objects.get_or_create(
        username="stripe_webhook_user", email="dev+stripe_webhook_user@whoknows.com"
    )
    return stripe_webhook_user


@receiver(WEBHOOK_SIGNALS["customer.subscription.updated"], sender=Event)
def on_subscription_update_ensure_items_updated(event: Event, **kwargs):
    if acct := event.customer.subscriber:
        try:
            subscription: Optional[MultiPlanSubscription] = acct.subscription
        except MultipleSubscriptionException as e:
            logger.exception(e)
            return
        else:
            if not subscription:
                return
    else:
        return

    subscription.sync_or_purge_subscription_items()


@receiver(WEBHOOK_SIGNALS["invoice.payment_succeeded"], sender=Event)
def on_payment_succeed_replenish_customer_credits(event: Event, **kwargs):
    if acct := event.customer.subscriber:
        try:
            subscription: Optional[MultiPlanSubscription] = acct.subscription
        except MultipleSubscriptionException as e:
            logger.exception(e)
            return
        else:
            if not subscription:
                return
    else:
        return

    subscription.sync_or_purge_subscription_items()

    quantity = 0
    for item in subscription.items.all():
        item: SubscriptionItem = item
        if item.plan.product.metadata.get("product") == "credits":
            quantity += item.quantity

    acct.replenish_credits(
        amount=quantity, initiated_by=get_stripe_webhook_user(), evidence=(event,)
    )
