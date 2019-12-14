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


class Group(AbstractOrganization):
    class Meta:
        verbose_name = _("group")
        verbose_name_plural = _("groups")

    def get_or_add_user(self, user, **kwargs):
        """
        Same as super(), but
         - skips making owner an Admin
         - adds credentials group permissions
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
            creds_group = self.organization.credentials_authgroup
            user.groups.remove(creds_group)
        if created:
            # User added signal
            user_added.send(sender=self, user=user)
        return org_user, created

    def add_user(self, *args, **kwargs):
        raise DeprecationWarning("Use `get_or_add_user` instead.")

    @property
    def credentials_authgroup(self):
        group, created = authGroup.objects.get_or_create(
            name=f"{self.slug}:developer_keys"
        )
        if created:
            assign_perm("add_organizationcredentials", group, self)  # object level
            assign_perm("users.add_organizationcredentials", group)  # global
            assign_perm("users.view_organizationcredentials", group)
            assign_perm("users.delete_organizationcredentials", group)
        return group

    def update_credentials_group(self, credentials=None):

        assign_perm(
            "delete_organizationcredentials",
            self.credentials_authgroup,
            credentials or self.credentials,
        )
        assign_perm(
            "view_organizationcredentials",
            self.credentials_authgroup,
            credentials or self.credentials,
        )

    @transaction.atomic
    def change_owner(self, new_owner):
        creds_group = self.organization.credentials_authgroup
        from_user = self.owner.organization_user.user
        from_user.groups.remove(creds_group)

        super().change_owner(new_owner)

        to_user = new_owner.user
        to_user.groups.add(creds_group)


class Seat(AbstractOrganizationUser):
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

    @transaction.atomic
    def save(self, *args, **kwargs):
        if self.pk is not None:
            from_user = Seat.objects.get(pk=self.pk).user
            to_user = self.user
            creds_group = self.organization.credentials_authgroup
            if from_user.groups.filter(name=creds_group.name).exists():
                from_user.groups.remove(creds_group)
                to_user.groups.add(creds_group)
        super().save(*args, **kwargs)


class GroupOwner(AbstractOrganizationOwner):
    class Meta:
        verbose_name = _("network admin")
        verbose_name_plural = _("network admins")


def make_key():
    return token_urlsafe(32)


def make_secret():
    return token_hex(32)


class OrganizationCredentials(TimeStampedModel):
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

    @property
    def api_key(self):
        return "{liveness}_{key}".format(
            liveness="test" if self.test_key else "live", key=self.key
        )

    def save(self, *args, **kwargs):
        new = False
        if not self.pk:
            new = True
        super().save(*args, **kwargs)
        if new:
            self.group.update_credentials_group(credentials=self)
