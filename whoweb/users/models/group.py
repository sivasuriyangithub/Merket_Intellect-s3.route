from allauth.account.models import EmailAddress
from django.db import models
from django.utils.translation import ugettext_lazy as _
from organizations.abstract import AbstractOrganization, AbstractOrganizationOwner
from organizations.abstract import AbstractOrganizationUser


class Group(AbstractOrganization):
    class Meta:
        verbose_name = _("group")
        verbose_name_plural = _("groups")


class GroupOwner(AbstractOrganizationOwner):
    class Meta:
        verbose_name = _("network admin")
        verbose_name_plural = _("network admins")

    def save(self, *args, **kwargs):
        if self.seat and not self.user:
            self.user = self.seat.user
        elif not self.seat and self.user and self.organization:
            self.seat, created = self.organization.get_or_add_user(self.user)
        super().save(*args, **kwargs)


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
        return EmailAddress.objects.get_primary(user=self.user)
