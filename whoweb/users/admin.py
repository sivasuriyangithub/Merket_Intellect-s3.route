from django.contrib import admin
from django.contrib.auth import admin as auth_admin
from django.contrib.auth import get_user_model
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
    verbose_name_plural = "profile"
    fields = (
        "pk",
        "public_id",
        "xperweb_id",
    )
    readonly_fields = ("pk", "public_id")


class UserAdmin(GuardedModelAdminMixin, auth_admin.UserAdmin):
    search_fields = (
        "email",
        "first_name",
        "last_name",
        "profile__xperweb_id",
        "username",
    )
    list_filter = ("is_active", "is_staff")
    list_display = ("email", "first_name", "last_name", "is_staff")
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
        (None, {"fields": ("email", "password")}),
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
    readonly_fields = (
        "last_login",
        "date_joined",
    )

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return list()
        return super(UserAdmin, self).get_inline_instances(request, obj)


class GroupOwnerInline(BaseOwnerInline):
    model = GroupOwner
    form = GroupOwnerAdminForm


class SeatInline(admin.TabularInline):
    model = Seat
    form = SeatAdminForm
    extra = 0
    raw_id_fields = ("user",)


class GroupAdmin(GuardedModelAdminMixin, BaseOrganizationAdmin):
    inlines = [GroupOwnerInline, SeatInline]
    actions = ["grant_default_permissions_to_all_seats"]

    def grant_default_permissions_to_all_seats(self, request, queryset):
        for group in queryset:
            for seat in group.organization_users.all():
                seat.user.groups.add(*group.default_permission_groups)
                if seat.is_admin:
                    seat.user.groups.add(*group.default_admin_permission_groups)


class SeatAdmin(GuardedModelAdminMixin, BaseOrganizationUserAdmin):
    form = SeatAdminForm
    search_fields = (
        "user__email",
        "user__profile__xperweb_id",
        "user__username",
    )


class GroupOwnerAdmin(GuardedModelAdminMixin, BaseOrganizationOwnerAdmin):
    form = GroupOwnerAdminForm
    search_fields = (
        "user__email",
        "user__profile__xperweb_id",
        "user__username",
    )


#
# class PermissionsAuthGroupAdmin(GuardedModelAdminMixin, AuthGroupAdmin):
#     pass
#

# admin.site.unregister(User)
admin.site.register(User, UserAdmin)

admin.site.unregister(Organization)
admin.site.unregister(OrganizationUser)
admin.site.unregister(OrganizationOwner)
# admin.site.unregister(AuthGroup)

admin.site.register(Group, GroupAdmin)
admin.site.register(Seat, SeatAdmin)
admin.site.register(GroupOwner, GroupOwnerAdmin)
admin.site.register(DeveloperKey, GuardedModelAdmin)
# admin.site.register(AuthGroup, PermissionsAuthGroupAdmin)
