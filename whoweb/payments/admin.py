from django.contrib import admin
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
)


class OwnerInline(BaseOwnerInline):
    model = BillingAccountOwner


class MemberInline(admin.TabularInline):
    model = BillingAccountMember
    form = BillingAccountMemberAdminInlineForm
    fields = ("is_admin", "seat", "seat_credits", "seat_trial_credits", "pool_credits")
    extra = 1


class BillingAccountAdmin(BaseOrganizationAdmin):
    inlines = [OwnerInline, MemberInline]


class BillingAccountMemberAdmin(BaseOrganizationUserAdmin):
    form = BillingAccountMemberAdminForm
    exclude = ("user",)

    def save_model(self, request, obj, form, change):
        obj.user = obj.seat.user
        super().save_model(request, obj, form, change)

    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj=obj)
        if obj and obj.pool_credits:
            try:
                fields.remove("seat_credits")
                fields.remove("seat_trial_credits")
            except ValueError:
                pass
        return fields

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.pool_credits:
            return ["credits", "trial_credits"]

        return super().get_readonly_fields(request, obj=obj)


class BillingAccountOwnerAdmin(BaseOrganizationOwnerAdmin):
    pass


admin.site.register(BillingAccount, BillingAccountAdmin)
admin.site.register(BillingAccountMember, BillingAccountMemberAdmin)
admin.site.register(BillingAccountOwner, BillingAccountOwnerAdmin)
