from typing import TYPE_CHECKING

from django.db import models
from django.utils.translation import ugettext_lazy as _
from djstripe.enums import PlanInterval
from djstripe.models import Plan
from model_utils.models import SoftDeletableModel

from whoweb.contrib.fields import ObscureIdMixin

if TYPE_CHECKING:
    from whoweb.search.models import ResultProfile


class AbstractPlanModel(ObscureIdMixin, models.Model):
    class Meta:
        abstract = True

    marketing_name = models.CharField(max_length=150, blank=True)

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
    tag = models.CharField(max_length=50, unique=True, null=True, blank=True)
    description = models.TextField(blank=True, default="")
    stripe_plans_monthly = models.ManyToManyField(
        Plan,
        limit_choices_to={"active": True, "interval": PlanInterval.month},
        related_name="monthly_presets",
    )
    stripe_plans_yearly = models.ManyToManyField(
        Plan,
        limit_choices_to={"active": True, "interval": PlanInterval.year},
        related_name="yearly_presets",
    )
    defaults = models.ManyToManyField(
        Plan, limit_choices_to={"active": True,}, related_name="+", blank=True
    )
    trial_days_allowed = models.PositiveSmallIntegerField(default=14)

    class Meta:
        verbose_name = _("credit plan factory")
        verbose_name_plural = _("credit plan factories")

    def create(self):
        return WKPlan.objects.create(
            marketing_name=self.marketing_name,
            credits_per_enrich=self.credits_per_enrich,
            credits_per_work_email=self.credits_per_work_email,
            credits_per_personal_email=self.credits_per_personal_email,
            credits_per_phone=self.credits_per_phone,
        )
