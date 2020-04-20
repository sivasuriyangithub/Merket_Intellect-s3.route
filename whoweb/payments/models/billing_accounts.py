from copy import copy, deepcopy
from datetime import datetime
from typing import Optional, Union

from django.contrib.postgres.fields import JSONField
from django.db import models
from django.db.models import F, Value
from django.db.models.functions import Greatest
from django.db.transaction import atomic
from django.utils.functional import cached_property
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _
from djstripe import settings as djstripe_settings
from djstripe.models import Customer, StripeModel, Subscription
from organizations.abstract import (
    AbstractOrganization,
    AbstractOrganizationUser,
    AbstractOrganizationOwner,
)
from organizations.signals import user_added
from proxy_overrides.related import ProxyForeignKey

from whoweb.accounting.actions import create_transaction, Debit, Credit
from whoweb.accounting.ledgers import (
    wkcredits_liability_ledger,
    wkcredits_fulfilled_ledger,
    wkcredits_sold_ledger,
    wkcredits_expired_ledger,
)
from whoweb.accounting.models import LedgerEntry
from whoweb.contrib.fields import ObscureIdMixin
from whoweb.users.models import Seat, Group
from .plans import WKPlan


class BillingAccount(ObscureIdMixin, AbstractOrganization):
    group = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True)
    seats = models.ManyToManyField(
        Seat, related_name="billing_account", through="BillingAccountMember"
    )

    plan = models.OneToOneField(WKPlan, on_delete=models.SET_NULL, null=True)
    plan_history = JSONField(null=True, blank=True, default=dict)
    credit_pool = models.IntegerField(default=0, blank=True)

    class Meta:
        verbose_name = _("billing account")
        verbose_name_plural = _("billing accounts")

    @cached_property
    def email(self):
        return self.owner.organization_user.seat.email

    @property
    def credits(self) -> int:
        return self.credit_pool + sum(
            self.organization_users.filter(pool_credits=False).values_list(
                "seat_credits", flat=True
            )
        )

    @property
    def customer(self) -> "MultiPlanCustomer":
        customer, created = MultiPlanCustomer.get_or_create(subscriber=self)
        return MultiPlanCustomer.objects.get(pk=customer.pk)

    def subscription(self):
        return self.customer.subscription

    def get_or_add_user(self, user, **kwargs):
        """
        Adds a new user to the organization, and if it's the first user makes
        the user an admin and the owner. Uses the `get_or_create` method to
        create or return the existing user.

        `user` should be a user instance, e.g. `auth.User`.

        Returns the same tuple as the `get_or_create` method, the
        `OrganizationUser` and a boolean value indicating whether the
        OrganizationUser was created or not.
        """
        users_count = self.users.all().count()
        kwargs.setdefault("is_admin", users_count == 0)

        org_user, created = self._org_user_model.objects.get_or_create(
            organization=self, user=user, defaults=kwargs
        )
        if users_count == 0:
            self._org_owner_model.objects.create(
                organization=self, organization_user=org_user
            )
        if created:
            # User added signal
            user_added.send(sender=self, user=user)
        return org_user, created

    @atomic
    def consume_credits(self, amount, *args, evidence=(), **kwargs):
        updated = BillingAccount.objects.filter(
            pk=self.pk, credit_pool__gte=amount
        ).update(credit_pool=F("credit_pool") - amount,)
        if updated:
            record_transaction_consume_credits(
                amount, *args, evidence=evidence + (self,), **kwargs
            )
        return bool(updated)

    @atomic
    def refund_credits(self, amount, *args, evidence=(), **kwargs):
        self.credit_pool = F("credit_pool") + amount
        self.save()
        record_transaction_refund_credits(
            amount, *args, evidence=evidence + (self,), **kwargs
        )

    @atomic
    def add_credits(self, amount, *args, evidence=(), **kwargs):
        self.credit_pool = F("credit_pool") + amount
        self.save()
        record_transaction_sold_credits(
            amount, *args, evidence=evidence + (self,), **kwargs
        )

    @atomic
    def expire_all_remaining_credits(self, *args, evidence=(), **kwargs):
        record_transaction_expire_credits(
            amount=int(self.credit_pool), *args, evidence=evidence + (self,), **kwargs
        )
        self.credit_pool = 0
        self.save()

    @atomic
    def replenish_credits(self, amount, *args, evidence=(), **kwargs):
        self.expire_all_remaining_credits(*args, evidence=evidence, **kwargs)
        self.add_credits(amount, *args, evidence=evidence, **kwargs)

    @atomic
    def allocate_credits_to_member(
        self, member: "BillingAccountMember", amount: int, trial_amount=0
    ):
        updated = BillingAccount.objects.filter(
            pk=self.pk, credit_pool__gte=amount
        ).update(credit_pool=F("credit_pool") - amount,)
        if updated:
            member.pool_credits = False
            member.seat_credits = F("seat_credits") + amount
            member.save()
        return bool(updated)

    @atomic
    def revoke_credits_from_member(self, member: "BillingAccountMember", amount: int):
        updated = BillingAccountMember.objects.filter(
            pk=member.pk, seat_credits__gte=amount
        ).update(seat_credits=F("seat_credits") - amount,)
        if updated:
            self.credit_pool = F("credit_pool") + amount
            self.save()
        return bool(updated)

    def set_member_credits(self, member: "BillingAccountMember", target: int):
        with atomic():
            locked_member = BillingAccountMember.objects.filter(
                pk=member.pk
            ).select_for_update(of=("self",))
            adjustment = target - locked_member.seat_credits
            # TODO: not sure if update can be done in subtransaction; test!
            if adjustment > 0:
                return self.allocate_credits_to_member(member, amount=adjustment)
            elif adjustment < 0:
                return self.revoke_credits_from_member(member, amount=adjustment)
            else:
                return True

    def update_plan(self, initiated_by, new_plan, with_credits=None):
        if self.plan is not None:
            old_plan = copy(self.plan.pk)
            self.plan_history[old_plan] = now().isoformat()
        if with_credits is not None and with_credits > self.credits:
            self.add_credits(
                amount=with_credits - self.credits, initiated_by=initiated_by
            )
        self.plan = new_plan
        self.save()

    def set_pool_for_all_members(self):
        return self.organization_users.update(pool_credits=True)


class BillingAccountMember(ObscureIdMixin, AbstractOrganizationUser):
    seat = models.OneToOneField(
        Seat,
        verbose_name="group seat",
        related_name="billing",
        on_delete=models.PROTECT,
    )
    seat_credits = models.IntegerField(default=0)
    pool_credits = models.BooleanField(default=False)

    class Meta:
        verbose_name = _("billing account member")
        verbose_name_plural = _("billing account members")

    @property
    def credits(self) -> int:
        if self.pool_credits:
            return self.organization.credit_pool
        return self.seat_credits

    @property
    def plan(self) -> Optional[WKPlan]:
        return self.organization.plan

    @atomic
    def consume_credits(self, amount, *args, evidence=(), **kwargs):
        if self.pool_credits:
            return self.organization.consume_credits(
                amount, *args, evidence=evidence + (self,), **kwargs
            )
        updated = BillingAccountMember.objects.filter(
            pk=self.pk, seat_credits__gte=amount
        ).update(seat_credits=F("seat_credits") - amount,)
        if updated:
            record_transaction_consume_credits(
                amount, *args, evidence=evidence + (self,), **kwargs
            )
        return bool(updated)

    @atomic
    def refund_credits(self, amount, *args, evidence=(), **kwargs):
        if self.pool_credits:
            return self.organization.refund_credits(
                amount, *args, evidence=evidence + (self,), **kwargs
            )
        self.seat_credits = F("seat_credits") + amount
        self.save()
        record_transaction_refund_credits(
            amount, *args, evidence=evidence + (self,), **kwargs
        )


class BillingAccountOwner(AbstractOrganizationOwner):
    class Meta:
        verbose_name = _("billing account owner")
        verbose_name_plural = _("billing account owners")


class MultiPlanCustomer(Customer):
    class Meta:
        proxy = True

    def has_active_subscription(self, plan=None):
        """
        Checks to see if this customer has an active subscription to the given plan.

        :param plan: The plan for which to check for an active subscription.
            If plan is None and there exists only one active subscription,
            this method will check if that subscription is valid.
            Calling this method with no plan and multiple valid subscriptions
            for this customer will throw an exception.
        :type plan: Plan or string (plan ID)

        :returns: True if there exists an active subscription, False otherwise.
        :throws: TypeError if ``plan`` is None and more than one active subscription
            exists for this customer.
        """

        if plan is None:
            return super().has_active_subscription()

        else:
            # Convert Plan to id
            if isinstance(plan, StripeModel):
                plan = plan.id
            return any(
                [
                    subscription.is_valid()
                    for subscription in self.subscriptions.filter(items__plan__id=plan)
                ]
            )

    def subscribe(
        self,
        plan=None,
        items=None,
        charge_immediately=True,
        application_fee_percent=None,
        coupon=None,
        quantity=None,
        metadata=None,
        tax_percent=None,
        billing_cycle_anchor=None,
        trial_end: Union[str, None, datetime] = None,
        trial_from_plan=None,
        trial_period_days=None,
    ):
        kwargs = dict(
            customer=self.id,
            application_fee_percent=application_fee_percent,
            coupon=coupon,
            quantity=quantity,
            metadata=metadata,
            billing_cycle_anchor=billing_cycle_anchor,
            tax_percent=tax_percent,
            trial_end=trial_end,
            trial_from_plan=trial_from_plan,
            trial_period_days=trial_period_days,
        )
        # Convert Plan to id
        if plan is not None and isinstance(plan, StripeModel):
            plan = plan.id
        if plan:
            kwargs["plan"] = plan
        if items:
            kwargs["items"] = items
        stripe_subscription = Subscription._api_create(**kwargs)

        if charge_immediately:
            self.send_invoice()

        return Subscription.sync_from_stripe_data(stripe_subscription)


class MultiPlanSubscription(Subscription):
    class Meta:
        proxy = True

    customer = ProxyForeignKey(
        MultiPlanCustomer,
        on_delete=models.CASCADE,
        related_name="subscriptions",
        help_text="The customer associated with this subscription.",
    )

    def update(
        self,
        plan=None,
        items=None,
        application_fee_percent=None,
        billing_cycle_anchor=None,
        coupon=None,
        prorate=djstripe_settings.PRORATION_POLICY,
        proration_date=None,
        metadata=None,
        quantity=None,
        tax_percent=None,
        trial_end=None,
    ):
        """
        See `MultiPlanCustomer.subscribe()`
        """

        # Convert Plan to id
        if plan is not None and isinstance(plan, StripeModel):
            plan = plan.id

        kwargs = deepcopy(locals())
        del kwargs["self"]

        items_for_manual_deletion = []
        if items is not None:
            patch_items_by_id = {item["plan"]: item for item in items}
            current_items_by_id = {item.plan.id: item for item in self.items.all()}

            settable_items = []
            for plan_id, patch_item in patch_items_by_id.items():
                if plan_id in current_items_by_id:
                    patch_item["id"] = current_items_by_id[plan_id].id
                settable_items.append(patch_item)
            for plan_id, existing_item in current_items_by_id.items():
                if plan_id not in patch_items_by_id:
                    settable_items.append(
                        {"plan": plan_id, "id": existing_item.id, "deleted": True}
                    )
                    items_for_manual_deletion.append(existing_item)
            kwargs["items"] = settable_items

        stripe_subscription = self.api_retrieve()

        for kwarg, value in kwargs.items():
            if value is not None:
                setattr(stripe_subscription, kwarg, value)

        subscription = Subscription.sync_from_stripe_data(stripe_subscription.save())

        for item in items_for_manual_deletion:
            item.delete()

        return MultiPlanSubscription.objects.get(pk=subscription.pk)


def record_transaction_consume_credits(
    amount, initiated_by, evidence=(), notes="", transaction_kind=None, posted_at=None
):
    create_transaction(
        user=initiated_by,
        ledger_entries=(
            LedgerEntry(ledger=wkcredits_liability_ledger(), amount=Debit(amount)),
            LedgerEntry(ledger=wkcredits_fulfilled_ledger(), amount=Credit(amount)),
        ),
        evidence=evidence,
        notes=notes,
        kind=transaction_kind,
        posted_timestamp=posted_at,
    )


def record_transaction_refund_credits(
    amount, initiated_by, evidence=(), notes="", transaction_kind=None, posted_at=None
):
    create_transaction(
        user=initiated_by,
        ledger_entries=(
            LedgerEntry(ledger=wkcredits_liability_ledger(), amount=Credit(amount)),
            LedgerEntry(ledger=wkcredits_fulfilled_ledger(), amount=Debit(amount)),
        ),
        evidence=evidence,
        notes=notes,
        kind=transaction_kind,
        posted_timestamp=posted_at,
    )


def record_transaction_sold_credits(
    amount,
    initiated_by=None,
    evidence=(),
    notes="",
    transaction_kind=None,
    posted_at=None,
):
    create_transaction(
        user=initiated_by,
        ledger_entries=(
            LedgerEntry(ledger=wkcredits_sold_ledger(), amount=Debit(amount)),
            LedgerEntry(ledger=wkcredits_liability_ledger(), amount=Credit(amount)),
        ),
        evidence=evidence,
        notes=notes,
        kind=transaction_kind,
        posted_timestamp=posted_at,
    )


def record_transaction_expire_credits(
    amount,
    initiated_by=None,
    evidence=(),
    notes="",
    transaction_kind=None,
    posted_at=None,
):
    create_transaction(
        user=initiated_by,
        ledger_entries=(
            LedgerEntry(ledger=wkcredits_liability_ledger(), amount=Credit(amount)),
            LedgerEntry(ledger=wkcredits_expired_ledger(), amount=Debit(amount)),
        ),
        evidence=evidence,
        notes=notes,
        kind=transaction_kind,
        posted_timestamp=posted_at,
    )
