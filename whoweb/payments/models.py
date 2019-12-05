from typing import Optional
from typing import TYPE_CHECKING


from django.db import models
from django.db.models import F, Value
from django.db.models.functions import Greatest
from django.db.transaction import atomic
from django.utils.translation import ugettext_lazy as _
from organizations.abstract import (
    AbstractOrganization,
    AbstractOrganizationUser,
    AbstractOrganizationOwner,
)
from organizations.signals import user_added

from whoweb.accounting.actions import create_transaction, Debit, Credit
from whoweb.accounting.models import Ledger, LedgerEntry
from whoweb.accounting.ledgers import (
    wkcredits_liability_ledger,
    wkcredits_fulfilled_ledger,
)
from whoweb.core.utils import PERSONAL_DOMAINS
from whoweb.users.models import Seat, Group

if TYPE_CHECKING:
    from whoweb.search.models import ResultProfile


class WKPlan(models.Model):
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

    def compute_contact_credit_use(self, profile: "ResultProfile"):
        work = False
        personal = False
        phone = any(profile.graded_phones)
        for graded_email in profile.sorted_graded_emails:
            email = graded_email.email
            if email and email.lower().split("@")[1] in PERSONAL_DOMAINS:
                personal = True
            if email and email.lower().split("@")[1] not in PERSONAL_DOMAINS:
                work = True
            if work and personal:
                break
        return sum(
            [
                work * self.credits_per_work_email,
                personal * self.credits_per_personal_email,
                phone * self.credits_per_phone,
            ]
        )


class BillingAccount(AbstractOrganization):
    group = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True)
    seats = models.ManyToManyField(
        Seat, related_name="billing_account", through="BillingAccountMember"
    )

    plan = models.ForeignKey(WKPlan, on_delete=models.SET_NULL, null=True)
    credit_pool = models.IntegerField(default=0, blank=True)
    trial_credit_pool = models.IntegerField(default=0, blank=True)

    class Meta:
        verbose_name = _("billing account")
        verbose_name_plural = _("billing accounts")

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


class BillingAccountMember(AbstractOrganizationUser):
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
