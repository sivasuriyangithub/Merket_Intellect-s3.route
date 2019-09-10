from django.db import models
from django.db.models import F, Value
from django.db.models.functions import Greatest
from django.utils.translation import ugettext_lazy as _
from organizations.abstract import (
    AbstractOrganization,
    AbstractOrganizationUser,
    AbstractOrganizationOwner,
)
from organizations.models import Organization


class BillingAccount(AbstractOrganization):
    org = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True)

    class Meta:
        verbose_name = _("billing account")
        verbose_name_plural = _("billing accounts")


class BillingAccountMember(AbstractOrganizationUser):
    class Meta:
        verbose_name = _("billing account seat")
        verbose_name_plural = _("billing account seats")

    organization = models.ForeignKey(
        BillingAccount,
        related_name="organization_users",
        on_delete=models.CASCADE,
        verbose_name="billing account",
    )
    credits = models.IntegerField(default=0)
    trial_credits = models.IntegerField(default=0)

    def get_or_add_org_user(self):
        return self.organization.org.get_or_add_user(self.user)

    def charge(self, amount=0):
        updated = (
            self.objects.filter(user=self.user, credits__gte=amount)
            .update(
                credits=F("credits") - amount,
                trial_credits=Greatest(F("trial_credits") - amount, Value(0)),
            )
            .count()
        )
        return amount if updated == 1 else 0

    def refund(self, amount=0):
        self.credits = F("credits") + amount
        self.save()


class BillingAccountOwner(AbstractOrganizationOwner):
    class Meta:
        verbose_name = _("billing account owner")
        verbose_name_plural = _("billing account owners")

    organization_user = models.OneToOneField(
        BillingAccountMember,
        on_delete=models.CASCADE,
        verbose_name="billing account seat",
    )
    organization = models.OneToOneField(
        BillingAccount,
        related_name="owner",
        on_delete=models.CASCADE,
        verbose_name="billing account",
    )
