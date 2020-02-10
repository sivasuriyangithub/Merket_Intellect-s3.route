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

from whoweb.contrib.fields import ObscureIdMixin


class Group(ObscureIdMixin, AbstractOrganization):
    class Meta:
        verbose_name = _("network")
        verbose_name_plural = _("networks")
        permissions = (
            ("add_developerkeys", "May add credentials for this organization"),
            ("add_seats", "May add seats to this organization"),
        )

    @property
    def permissions_scope(self):
        return f"org.{self.slug}"

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
            if created:
                user.groups.add(*self.default_admin_permission_groups)

        if created:
            # User added signal
            user_added.send(sender=self, user=user)
            user.groups.add(*self.default_permission_groups)
        return org_user, created

    @property
    @transaction.atomic
    def default_admin_permission_groups(self):
        return [self.credentials_admin_authgroup, self.seat_admin_authgroup]

    @property
    @transaction.atomic
    def default_permission_groups(self):
        return [self.seat_viewers, self.network_viewers]

    def add_user(self, user, **kwargs):
        return self.get_or_add_user(user, **kwargs)[0]

    @transaction.atomic
    def remove_user(self, user):
        group_authGroups = authGroup.objects.filter(
            name__startswith=f"{self.permissions_scope}:"
        )
        user.groups.remove(*list(group_authGroups))
        super().remove_user(user)

    @property
    def credentials_admin_authgroup(self):
        group, created = authGroup.objects.get_or_create(
            name=f"{self.permissions_scope}:developer_keys_admin"
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
            name=f"{self.permissions_scope}:seat_admin"
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
            name=f"{self.permissions_scope}:seat_viewers"
        )
        if created:
            assign_perm("users.view_seat", group)
        return group

    @property
    def network_viewers(self):
        group, created = authGroup.objects.get_or_create(
            name=f"{self.permissions_scope}:network_viewers"
        )
        if created:
            assign_perm("users.view_group", group)
            assign_perm("users.view_group", group, self)
        return group

    @transaction.atomic
    def change_owner(self, new_owner: "Seat"):
        from_user = self.owner.organization_user.user
        admin_groups = list(
            from_user.groups.filter(name__startswith=f"{self.permissions_scope}:")
        )
        from_user.groups.remove(*admin_groups)
        from_user.groups.add(*self.default_permission_groups)

        super().change_owner(new_owner)

        to_user = new_owner.user
        to_user.groups.add(*admin_groups)


class Seat(ObscureIdMixin, AbstractOrganizationUser):
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

    def __unicode__(self):
        return "{0} ({1})".format(
            self.name or ("User: " + self.user_id), self.organization.name
        )

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

    @property
    def user(self):
        return self.organization_user.user


def make_key():
    return token_urlsafe(32)


def make_secret():
    return token_hex(32)


class DeveloperKey(ObscureIdMixin, TimeStampedModel):
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
