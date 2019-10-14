from django.db import models
from django.db.models import F, Value
from django.db.models.functions import Greatest
from django.utils.translation import ugettext_lazy as _
from organizations.abstract import (
    AbstractOrganization,
    AbstractOrganizationUser,
    AbstractOrganizationOwner,
)

from whoweb.users.models import Seat, Group


class BillingAccount(AbstractOrganization):
    group = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True)
    seats = models.ManyToManyField(
        Seat, related_name="billing_account", through="BillingAccountMember"
    )

    credit_pool = models.IntegerField(default=0, blank=True)
    trial_credit_pool = models.IntegerField(default=0, blank=True)

    class Meta:
        verbose_name = _("billing account")
        verbose_name_plural = _("billing accounts")

    def charge(self, amount=0):
        updated = (
            self.objects.filter(pk=self.pk, credit_pool__gte=amount)
            .update(
                credit_pool=F("credit_pool") - amount,
                trial_credit_pool=Greatest(F("trial_credit_pool") - amount, Value(0)),
            )
            .count()
        )
        return amount if updated == 1 else 0

    def refund(self, amount=0):
        self.credit_pool = F("credit_pool") + amount
        self.save()


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
    def credits(self):
        if self.pool_credits:
            return self.organization.credit_pool
        return self.seat_credits

    @property
    def trial_credits(self):
        if self.pool_credits:
            return self.organization.trial_credit_pool
        return self.seat_trial_credits

    def charge(self, amount=0):
        updated = (
            self.objects.filter(pk=self.pk, seat_credits__gte=amount)
            .update(
                seat_credits=F("seat_credits") - amount,
                seat_trial_credits=Greatest(F("seat_trial_credits") - amount, Value(0)),
            )
            .count()
        )
        return amount if updated == 1 else 0

    def refund(self, amount=0):
        self.seat_credits = F("seat_credits") + amount
        self.save()


class BillingAccountOwner(AbstractOrganizationOwner):
    class Meta:
        verbose_name = _("billing account owner")
        verbose_name_plural = _("billing account owners")
