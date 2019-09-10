from django.contrib import admin

from organizations.base_admin import BaseOrganizationAdmin
from organizations.base_admin import BaseOrganizationOwnerAdmin
from organizations.base_admin import BaseOrganizationUserAdmin
from organizations.base_admin import BaseOwnerInline

from whoweb.payments.models import (
    BillingAccountOwner,
    BillingAccount,
    BillingAccountMember,
)


class OwnerInline(BaseOwnerInline):
    model = BillingAccountOwner


class AccountAdmin(BaseOrganizationAdmin):
    inlines = [OwnerInline]


class AccountUserAdmin(BaseOrganizationUserAdmin):
    pass


class AccountOwnerAdmin(BaseOrganizationOwnerAdmin):
    pass


admin.site.register(BillingAccount, AccountAdmin)
admin.site.register(BillingAccountMember, AccountUserAdmin)
admin.site.register(BillingAccountOwner, AccountOwnerAdmin)
