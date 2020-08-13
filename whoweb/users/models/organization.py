from secrets import token_urlsafe, token_hex

from allauth.account.models import EmailAddress
from django.db import models, transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import ugettext_lazy as _
from django_cryptography.fields import encrypt
from guardian.models import UserObjectPermissionBase, GroupObjectPermissionBase
from guardian.shortcuts import assign_perm
from model_utils import FieldTracker
from model_utils.models import TimeStampedModel
from organizations.abstract import AbstractOrganizationOwner, AbstractOrganization
from organizations.abstract import AbstractOrganizationUser

from whoweb.contrib.fields import ObscureIdMixin
from whoweb.contrib.organizations.models import (
    PermissionsAbstractOrganization,
    permissions_org_user_post_save,
)


class Group(ObscureIdMixin, PermissionsAbstractOrganization, AbstractOrganization):
    class Meta:
        verbose_name = _("network")
        verbose_name_plural = _("networks")
        permissions = (
            ("add_billing", "May add billing accounts in this organization"),
            ("add_developerkeys", "May add API credentials for this organization"),
            ("view_developerkeys", "May view all API credentials in this organization"),
            (
                "delete_developerkeys",
                "May delete API credentials from this organization",
            ),
            ("add_seats", "May add seats to this organization"),
            ("view_seats", "May view all seats in this organization"),
            ("delete_seats", "May delete seats from this organization"),
        )

    @property
    def permissions_scope(self):
        return f"org.{self.slug}"

    @property
    @transaction.atomic
    def default_admin_permission_groups(self):
        return [
            self.credentials_admin_authgroup,
            self.seat_admin_authgroup,
        ]

    @property
    @transaction.atomic
    def default_permission_groups(self):
        return [self.seat_viewers, self.network_viewers, self.billing_account_authgroup]

    @property
    def credentials_admin_authgroup(self):
        group, created = self.get_or_create_auth_group("developer_keys_admin")
        if created:
            assign_perm("add_developerkeys", group, self)
            assign_perm("view_developerkeys", group, self)
            assign_perm("delete_developerkeys", group, self)
            assign_perm("users.add_developerkey", group)
            assign_perm("users.view_developerkey", group)
            assign_perm("users.delete_developerkey", group)
        return group

    @property
    def seat_admin_authgroup(self):
        group, created = self.get_or_create_auth_group("seat_admin")
        if created:
            assign_perm("add_seats", group, self)
            assign_perm("view_seats", group, self)
            assign_perm("delete_seats", group, self)
            assign_perm("users.add_seat", group)
            assign_perm("users.view_seat", group)
            assign_perm("users.delete_seat", group)
        return group

    @property
    def billing_account_authgroup(self):
        group, created = self.get_or_create_auth_group("org_billing_manager")
        if created:
            assign_perm("add_billing", group, self)
            assign_perm("payments.add_billingaccount", group)
            assign_perm("payments.view_billingaccount", group)
        return group

    @property
    def seat_viewers(self):
        group, created = self.get_or_create_auth_group("seat_viewers")
        if created:
            assign_perm("view_seats", group, self)
            assign_perm("users.view_seat", group)
        return group

    @property
    def network_viewers(self):
        group, created = self.get_or_create_auth_group("network_viewers")
        if created:
            assign_perm("users.view_group", group)
            assign_perm("users.view_group", group, self)
        return group


class NetworkUserObjectPermission(UserObjectPermissionBase):
    content_object = models.ForeignKey(Group, on_delete=models.CASCADE)


class NetworkGroupObjectPermission(GroupObjectPermissionBase):
    content_object = models.ForeignKey(Group, on_delete=models.CASCADE)


class Seat(ObscureIdMixin, AbstractOrganizationUser):
    display_name = models.CharField(
        _("Name"),
        db_column="name",
        blank=True,
        max_length=255,
        help_text="How this seat should be labeled within their organization.",
    )
    title = models.CharField(
        blank=True, max_length=255, help_text="Title within organization"
    )
    is_active = models.BooleanField(_("active"), default=True)
    tracker = FieldTracker(fields=["is_admin"])

    class Meta:
        verbose_name = _("seat")
        verbose_name_plural = _("seats")

    def __unicode__(self):
        return "{0} ({1})".format(
            self.name or f"User: {self.user_id}", self.organization.name
        )

    @property
    def name(self):
        return self.display_name

    @property
    def email(self):
        return EmailAddress.objects.get_primary(user=self.user).email


class SeatUserObjectPermission(UserObjectPermissionBase):
    content_object = models.ForeignKey(Seat, on_delete=models.CASCADE)


class SeatGroupObjectPermission(GroupObjectPermissionBase):
    content_object = models.ForeignKey(Seat, on_delete=models.CASCADE)


class GroupOwner(AbstractOrganizationOwner):
    class Meta:
        verbose_name = _("network owner")
        verbose_name_plural = _("network owners")

    @property
    def user(self):
        return self.organization_user.user


def make_key():
    return token_urlsafe(32)


def make_secret():
    return token_hex(32)


class NetworkAdminUserObjectPermission(UserObjectPermissionBase):
    content_object = models.ForeignKey(GroupOwner, on_delete=models.CASCADE)


class NetworkAdminGroupObjectPermission(GroupObjectPermissionBase):
    content_object = models.ForeignKey(GroupOwner, on_delete=models.CASCADE)


class DeveloperKey(ObscureIdMixin, TimeStampedModel):
    key = models.CharField(default=make_key, unique=True, max_length=64)
    secret = encrypt(models.CharField(default=make_secret, max_length=64))
    test_key = models.BooleanField(default=False)
    network = models.ForeignKey(
        Group, on_delete=models.CASCADE, related_name="credentials"
    )
    seat = models.ForeignKey(
        Seat,
        null=True,
        on_delete=models.SET_NULL,
        related_name="credentials",
        blank=True,
    )
    created_by = models.ForeignKey("users.User", on_delete=models.SET_NULL, null=True)

    @property
    def api_key(self):
        return "{liveness}_{key}".format(
            liveness="test" if self.test_key else "live", key=self.key
        )


class DeveloperKeyUserObjectPermission(UserObjectPermissionBase):
    content_object = models.ForeignKey(DeveloperKey, on_delete=models.CASCADE)


class DeveloperKeyGroupObjectPermission(GroupObjectPermissionBase):
    content_object = models.ForeignKey(DeveloperKey, on_delete=models.CASCADE)


receiver(post_save, sender=Seat)(permissions_org_user_post_save)
