from copy import copy
from typing import Optional

from django.contrib.postgres.fields import JSONField
from django.db import models
from django.db.models import F, Value
from django.db.models.functions import Greatest
from django.db.transaction import atomic
from django.utils.functional import cached_property
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _
from djstripe.models import Customer, StripeModel
from organizations.abstract import (
    AbstractOrganization,
    AbstractOrganizationUser,
    AbstractOrganizationOwner,
)
from organizations.signals import user_added

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


class BillingAccount(ObscureIdMixin, AbstractOrganization):
    group = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True)
    seats = models.ManyToManyField(
        Seat, related_name="billing_account", through="BillingAccountMember"
    )

    plan = models.OneToOneField(WKPlan, on_delete=models.SET_NULL, null=True)
    plan_history = JSONField(null=True, blank=True, default=dict)
    credit_pool = models.IntegerField(default=0, blank=True)
    trial_credit_pool = models.IntegerField(default=0, blank=True)

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
    def customer(self) -> MultiPlanCustomer:
        customer, created = MultiPlanCustomer.get_or_create(subscriber=self)
        if not created:
            customer = MultiPlanCustomer.objects.get(pk=customer.pk)
        return customer

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
        ).update(
            credit_pool=F("credit_pool") - amount,
            trial_credit_pool=Greatest(F("trial_credit_pool") - amount, Value(0)),
        )
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
        self.trial_credit_pool = 0
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
            member.seat_trial_credits = F("seat_trial_credits") + trial_amount
            member.save()
        return bool(updated)

    @atomic
    def revoke_credits_from_member(self, member: "BillingAccountMember", amount: int):
        updated = BillingAccountMember.objects.filter(
            pk=member.pk, seat_credits__gte=amount
        ).update(
            seat_credits=F("seat_credits") - amount,
            seat_trial_credits=Greatest(F("seat_trial_credits") - amount, Value(0)),
        )
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
            if with_credits is not None:
                if with_credits > self.credits:
                    self.add_credits(
                        amount=with_credits - self.credits, initiated_by=initiated_by
                    )
        self.plan = new_plan
        self.save()


class BillingAccountMember(ObscureIdMixin, AbstractOrganizationUser):
    seat = models.OneToOneField(
        Seat,
        verbose_name="group seat",
        related_name="billing",
        on_delete=models.PROTECT,
    )
    seat_credits = models.IntegerField(default=0)
    seat_trial_credits = models.IntegerField(default=0)
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
    def trial_credits(self) -> int:
        if self.pool_credits:
            return self.organization.trial_credit_pool
        return self.seat_trial_credits

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
        ).update(
            seat_credits=F("seat_credits") - amount,
            seat_trial_credits=Greatest(F("seat_trial_credits") - amount, Value(0)),
        )
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
