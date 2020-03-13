from copy import copy
from typing import Optional
from typing import TYPE_CHECKING

from django.contrib.postgres.fields import JSONField
from django.db import models
from django.db.models import F, Value
from django.db.models.functions import Greatest
from django.db.transaction import atomic
from django.utils.functional import cached_property
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _
from djstripe.models import Plan, Customer
from model_utils.models import SoftDeletableModel
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
)
from whoweb.accounting.models import Ledger, LedgerEntry
from whoweb.contrib.fields import ObscureIdMixin
from whoweb.users.models import Seat, Group

if TYPE_CHECKING:
    from whoweb.search.models import ResultProfile


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


class AbstractPlanModel(ObscureIdMixin, models.Model):
    class Meta:
        abstract = True

    credits_per_enrich = models.IntegerField(
        default=5,
        verbose_name="Credits per Enrich",
        help_text="Number of credits charged for an enrich service call.",
    )
    credits_per_work_email = models.IntegerField(
        default=100,
        verbose_name="Credits per Work Derivation",
        help_text="Number of credits charged for a service call returning any work emails.",
    )
    credits_per_personal_email = models.IntegerField(
        default=300,
        verbose_name="Credits per Personal Derivation",
        help_text="Number of credits charged for a service call returning any personal emails.",
    )
    credits_per_phone = models.IntegerField(
        default=400,
        verbose_name="Credits per Phone Derivation",
        help_text="Number of credits charged for a service call returning any phone numbers.",
    )


class WKPlan(SoftDeletableModel, AbstractPlanModel):
    class Meta:
        verbose_name = _("credit plan")
        verbose_name_plural = _("credit plans")

    def compute_credit_use_types(self, graded_emails, graded_phones):
        work = False
        personal = False
        phone = any(graded_phones)
        for graded_email in graded_emails:
            if graded_email.is_passing and graded_email.is_personal:
                personal = True
            if graded_email.is_passing and graded_email.is_work:
                work = True
            if work and personal:
                break
        return work, personal, phone

    def compute_contact_credit_use(self, profile: "ResultProfile"):
        work, personal, phone = self.compute_credit_use_types(
            profile.graded_emails, profile.graded_phones
        )
        return sum(
            [
                work * self.credits_per_work_email,
                personal * self.credits_per_personal_email,
                phone * self.credits_per_phone,
            ]
        )

    def compute_additional_contact_info_credit_use(
        self, cached_emails, cached_phones, profile
    ):
        cached_work, cached_personal, cached_phone = self.compute_credit_use_types(
            cached_emails, cached_phones
        )
        work, personal, phone = self.compute_credit_use_types(
            profile.graded_emails, profile.graded_phones
        )
        return sum(
            [
                (work and not cached_work) * self.credits_per_work_email,
                (personal and not cached_personal) * self.credits_per_personal_email,
                (phone and not cached_phone) * self.credits_per_phone,
            ]
        )


class WKPlanPreset(AbstractPlanModel):
    stripe_plans = models.ManyToManyField(Plan, limit_choices_to={"active": True})

    class Meta:
        verbose_name = _("credit plan factory")
        verbose_name_plural = _("credit plan factories")

    def create(self):
        return WKPlan.objects.create(
            credits_per_enrich=self.credits_per_enrich,
            credits_per_work_email=self.credits_per_work_email,
            credits_per_personal_email=self.credits_per_personal_email,
            credits_per_phone=self.credits_per_phone,
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

    def subscription(self):
        customer, _created = Customer.get_or_create(subscriber=self)
        return customer.subscription

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
    def apply_credits(self, amount, *args, evidence=(), **kwargs):
        self.credit_pool = F("credit_pool") + amount
        self.save()
        record_transaction_sold_credits(
            amount, *args, evidence=evidence + (self,), **kwargs
        )

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

    def update_plan(self, new_plan, with_credits=None):
        if self.plan is not None:
            old_plan = copy(self.plan.pk)
            self.plan_history[old_plan] = now()
            if with_credits is not None:
                if with_credits > self.credits:
                    self.purchase_credits(with_credits - self.credits)
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
    amount, initiated_by, evidence=(), notes="", transaction_kind=None, posted_at=None
):
    create_transaction(
        user=initiated_by,
        ledger_entries=(
            LedgerEntry(ledger=wkcredits_sold_ledger(), amount=Credit(amount)),
            LedgerEntry(ledger=wkcredits_liability_ledger(), amount=Credit(amount)),
        ),
        evidence=evidence,
        notes=notes,
        kind=transaction_kind,
        posted_timestamp=posted_at,
    )
