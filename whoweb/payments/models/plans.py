from typing import TYPE_CHECKING

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _
from djstripe.enums import PlanInterval
from djstripe.models import Plan
from model_utils.models import SoftDeletableModel

from whoweb.contrib.fields import ObscureIdMixin

if TYPE_CHECKING:
    from whoweb.search.models import ResultProfile

User = get_user_model()


class AbstractPlanModel(ObscureIdMixin, models.Model):
    class Meta:
        abstract = True

    marketing_name = models.CharField(max_length=150, blank=True)

    permission_group = models.ForeignKey(
        Group,
        null=True,
        on_delete=models.PROTECT,
        help_text="Permissions group users will be placed in when on an active subscription to this plan.",
    )

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

    def validate_items(self, items):
        valid_monthly_plans = self.stripe_plans_monthly.in_bulk(field_name="id")
        valid_yearly_plans = self.stripe_plans_yearly.in_bulk(field_name="id")

        valid_items = []
        total_credits = 0
        at_least_one_non_addon_product = False
        for item in items:
            plan_id, quantity = item["stripe_id"], item["quantity"]
            if plan_id in valid_monthly_plans:
                plan = valid_monthly_plans[plan_id]
            elif plan_id in valid_yearly_plans:
                plan = valid_yearly_plans[plan_id]
            else:
                raise ValidationError("Invalid items.")
            if plan.product.metadata.get("product") == "credits":
                total_credits += quantity
            if plan.product.metadata.get("is_addon") == "false":
                at_least_one_non_addon_product = True
            valid_items.append({"plan": plan_id, "quantity": quantity})
        if not at_least_one_non_addon_product:
            raise ValidationError("Invalid items.")
        return valid_items, total_credits


class BillingPermissionGrant(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="billing_permission_grants"
    )
    permission_group = models.ForeignKey(Group, on_delete=models.CASCADE)
    plan = models.ForeignKey(
        WKPlan, on_delete=models.CASCADE, related_name="permission_grants"
    )
