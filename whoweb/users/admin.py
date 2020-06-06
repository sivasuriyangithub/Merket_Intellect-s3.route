from django.contrib import admin
from django.contrib.auth import admin as auth_admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.utils.translation import gettext_lazy as _
from guardian.admin import GuardedModelAdminMixin, GuardedModelAdmin
from organizations.base_admin import (
    BaseOrganizationAdmin,
    BaseOwnerInline,
    BaseOrganizationOwnerAdmin,
    BaseOrganizationUserAdmin,
)
from organizations.models import OrganizationOwner, OrganizationUser, Organization

from whoweb.users.forms import GroupOwnerAdminForm, SeatAdminForm
from whoweb.users.models import UserProfile, Group, Seat, GroupOwner, DeveloperKey

User = get_user_model()


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name = "profile"
    fields = ("pk", "public_id")
    readonly_fields = fields


@admin.register(User)
class UserAdmin(GuardedModelAdminMixin, auth_admin.UserAdmin):
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "username", "password1", "password2"),
            },
        ),
    )
    fieldsets = (
        (None, {"fields": ("email", "username", "password")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    inlines = [
        UserProfileInline,
    ]
    readonly_fields = ("last_login", "date_joined")


class GroupOwnerInline(BaseOwnerInline):
    model = GroupOwner
    form = GroupOwnerAdminForm


class GroupAdmin(GuardedModelAdminMixin, BaseOrganizationAdmin):
    inlines = [GroupOwnerInline]


class SeatAdmin(GuardedModelAdminMixin, BaseOrganizationUserAdmin):
    form = SeatAdminForm


class GroupOwnerAdmin(GuardedModelAdminMixin, BaseOrganizationOwnerAdmin):
    form = GroupOwnerAdminForm


admin.site.unregister(Organization)
admin.site.unregister(OrganizationUser)
admin.site.unregister(OrganizationOwner)
admin.site.register(Group, GroupAdmin)
admin.site.register(Seat, SeatAdmin)
admin.site.register(GroupOwner, GroupOwnerAdmin)
admin.site.register(DeveloperKey, GuardedModelAdmin)
admin.site.register(Permission)
