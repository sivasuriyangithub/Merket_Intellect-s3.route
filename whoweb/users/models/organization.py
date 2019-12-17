from secrets import token_urlsafe, token_hex

from allauth.account.models import EmailAddress
from django.contrib.auth.models import Group as authGroup
from django.db import models, transaction
from django.utils.translation import ugettext_lazy as _
from django_cryptography.fields import encrypt
from guardian.shortcuts import assign_perm
from model_utils.models import TimeStampedModel
from organizations.abstract import AbstractOrganization, AbstractOrganizationOwner
from organizations.abstract import AbstractOrganizationUser
from organizations.signals import user_added

from contrib.fields import ObscuredAutoField


class Group(AbstractOrganization):
    id = ObscuredAutoField(prefix="ntw", verbose_name="ID", primary_key=True)

    class Meta:
        verbose_name = _("network")
        verbose_name_plural = _("networks")
        permissions = (
            ("add_developerkeys", "May add credentials for this organization"),
            ("add_seats", "May add seats to this organization"),
        )

    def get_or_add_user(self, user, **kwargs):
        """
        Same as super(), but
         - allows for additional keyword user defaults
         - adds default and owner permission groups
        """

        users_count = self.users.all().count()
        kwargs.setdefault("is_admin", users_count == 0)

        org_user, created = self._org_user_model.objects.get_or_create(
            organization=self, user=user, defaults=kwargs
        )
        if users_count == 0:
            self._org_owner_model.objects.create(
                organization=self, organization_user=org_user
            )
            creds_group = self.organization.credentials_admin_authgroup
            if created:
                user.groups.add(creds_group)

        if created:
            # User added signal
            user_added.send(sender=self, user=user)
            user.groups.add(self.default_permission_groups)
        return org_user, created

    @transaction.atomic
    def default_permission_groups(self):
        return (self.seat_viewers, self.network_viewers)

    def add_user(self, user, **kwargs):
        return self.get_or_add_user(user, **kwargs)[0]

    @transaction.atomic
    def remove_user(self, user):
        super().remove_user(user)
        user.groups.remove(self.default_permission_groups)

    @property
    def credentials_admin_authgroup(self):
        group, created = authGroup.objects.get_or_create(
            name=f"{self.slug}:developer_keys_admin"
        )
        if created:
            assign_perm("add_developerkeys", group, self)  # object level
            assign_perm("users.add_developerkey", group)  # global
            assign_perm("users.view_developerkey", group)
            assign_perm("users.delete_developerkey", group)
        return group

    @property
    def seat_admin_authgroup(self):
        group, created = authGroup.objects.get_or_create(
            name=f"org:{self.slug}.seat_admin"
        )
        if created:
            assign_perm("add_seats", group, self)  # object level
            assign_perm("users.add_seat", group)  # global
            assign_perm("users.view_seat", group)
            assign_perm("users.delete_seat", group)
        return group

    @property
    def seat_viewers(self):
        group, created = authGroup.objects.get_or_create(
            name=f"org:{self.slug}.seat_viewers"
        )
        if created:
            assign_perm("users.view_seat", group)
        return group

    @property
    def network_viewers(self):
        group, created = authGroup.objects.get_or_create(
            name=f"org:{self.slug}.network)_viewers"
        )
        if created:
            assign_perm("users.view_group", group)
            assign_perm("users.view_group", group, self)
        return group

    @transaction.atomic
    def change_owner(self, new_owner):
        creds_group = self.organization.credentials_admin_authgroup
        from_user = self.owner.organization_user.user
        from_user.groups.remove(creds_group)

        super().change_owner(new_owner)

        to_user = new_owner.user
        to_user.groups.add(creds_group)


class Seat(AbstractOrganizationUser):
    id = ObscuredAutoField(prefix="seat", verbose_name="ID", primary_key=True)
    display_name = models.CharField(
        _("Name"),
        db_column="name",
        blank=True,
        max_length=255,
        help_text="How this seat should be labeled within their organization.",
    )
    is_active = models.BooleanField(_("active"), default=True)

    class Meta:
        verbose_name = _("seat")
        verbose_name_plural = _("seats")

    @property
    def name(self):
        return self.display_name

    @property
    def email(self):
        return EmailAddress.objects.get_primary(user=self.user).email


class GroupOwner(AbstractOrganizationOwner):
    class Meta:
        verbose_name = _("network admin")
        verbose_name_plural = _("network admins")


def make_key():
    return token_urlsafe(32)


def make_secret():
    return token_hex(32)


class DeveloperKey(TimeStampedModel):
    id = ObscuredAutoField(prefix="dk", verbose_name="ID", primary_key=True)
    key = models.CharField(default=make_key, unique=True, max_length=64)
    secret = encrypt(models.CharField(default=make_secret, max_length=64))
    test_key = models.BooleanField(default=False)
    group = models.ForeignKey(
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
