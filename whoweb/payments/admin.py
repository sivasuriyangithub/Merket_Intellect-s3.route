from admin_actions.admin import ActionsModelAdmin
from django.contrib import admin, messages
from django.shortcuts import redirect
from django.urls import reverse
from djstripe.models import Plan
from organizations.base_admin import BaseOrganizationAdmin
from organizations.base_admin import BaseOrganizationOwnerAdmin
from organizations.base_admin import BaseOrganizationUserAdmin
from organizations.base_admin import BaseOwnerInline

from whoweb.payments.admin_forms import (
    BillingAccountMemberAdminForm,
    BillingAccountMemberAdminInlineForm,
)
from whoweb.payments.models import (
    BillingAccountOwner,
    BillingAccount,
    BillingAccountMember,
    WKPlan,
    WKPlanPreset,
)


class OwnerInline(BaseOwnerInline):
    model = BillingAccountOwner


class MemberInline(admin.TabularInline):
    model = BillingAccountMember
    fields = ("is_admin", "seat", "seat_credits", "pool_credits")
    extra = 1
    readonly_fields = ("seat_credits",)


class BillingAccountAdmin(BaseOrganizationAdmin):
    inlines = [OwnerInline, MemberInline]
    list_display = ("pk", "public_id", "name", "network", "credit_pool")
    actions = ["grant_default_permissions_to_all_members"]

    def grant_default_permissions_to_all_members(self, request, queryset):
        for acct in queryset:
            for member in acct.organization_users.all():
                member.user.groups.add(*acct.default_permission_groups)
                if member.is_admin:
                    member.user.groups.add(*acct.default_admin_permission_groups)
            acct.grant_plan_permissions_for_members()


class BillingAccountMemberAdmin(BaseOrganizationUserAdmin):
    form = BillingAccountMemberAdminForm
    list_display = (
        "pk",
        "public_id",
        "user",
        "organization",
        "pool_credits",
        "credits",
    )
    exclude = ("user",)

    def save_model(self, request, obj, form, change):
        obj.user = obj.seat.user
        super().save_model(request, obj, form, change)

    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj=obj)
        if obj and obj.pool_credits:
            try:
                fields.remove("seat_credits")
            except ValueError:
                pass
        return fields

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.pool_credits:
            return [
                "credits",
            ]

        return super().get_readonly_fields(request, obj=obj)


class BillingAccountOwnerAdmin(BaseOrganizationOwnerAdmin):
    pass


class WKPlanAdmin(admin.ModelAdmin):
    list_display = (
        "pk",
        "public_id",
        "credits_per_enrich",
        "credits_per_work_email",
        "credits_per_personal_email",
        "credits_per_phone",
    )
    list_display_links = (
        "pk",
        "public_id",
    )
    fields = (
        "pk",
        "public_id",
        "credits_per_enrich",
        "credits_per_work_email",
        "credits_per_personal_email",
        "credits_per_phone",
        "permission_group",
    )
    readonly_fields = (
        "pk",
        "public_id",
    )


class StripePlanMonthlyInline(admin.TabularInline):
    model = WKPlanPreset.stripe_plans_monthly.through
    extra = 1

    verbose_name_plural = "Stripe Plans with Monthly Interval"


class StripePlanYearlyInline(admin.TabularInline):
    model = WKPlanPreset.stripe_plans_yearly.through
    extra = 1

    verbose_name_plural = "Stripe Plans with Yearly Interval"


class WKPlanPresetAdmin(ActionsModelAdmin):
    list_display = (
        "pk",
        "public_id",
        "tag",
        "credits_per_enrich",
        "credits_per_work_email",
        "credits_per_personal_email",
        "credits_per_phone",
    )
    list_display_links = (
        "pk",
        "public_id",
    )
    filter_horizontal = ("stripe_plans_monthly", "stripe_plans_yearly", "defaults")

    actions_list = ("sync",)

    def sync(self, request):
        for plan_data in Plan.api_list():
            plan = Plan.sync_from_stripe_data(plan_data)
            self.message_user(
                request, f"Synchronized plan  {plan.id}", level=messages.INFO
            )
        return redirect(reverse("admin:payments_wkplanpreset_changelist"))

    sync.short_description = "Synchronize Stripe Plans"


admin.site.register(BillingAccount, BillingAccountAdmin)
admin.site.register(BillingAccountMember, BillingAccountMemberAdmin)
admin.site.register(BillingAccountOwner, BillingAccountOwnerAdmin)
admin.site.register(WKPlan, WKPlanAdmin)
admin.site.register(WKPlanPreset, WKPlanPresetAdmin)
