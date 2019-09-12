from allauth.account.models import EmailAddress
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import CharField
from django.utils.translation import ugettext_lazy as _
from model_utils.models import TimeStampedModel
from organizations.abstract import (
    AbstractOrganization,
    AbstractOrganizationUser,
    AbstractOrganizationOwner,
)


class User(AbstractUser):
    """
    Generally, only auth or permissions related fields should exist on this model.
    See UserProfile below for custom fields that should be one-to-one with a user.
    """

    email = models.EmailField(
        _("email address"),
        unique=True,
        help_text="Required. Verification handled in Admin>Accounts>Email addresses",
        error_messages={"unique": _("A user with that email already exists.")},
    )

    def get_username(self):
        """Return the username for this User."""
        return str(getattr(self, self.EMAIL_FIELD))

    def get_full_name(self):
        """Return the username for this User."""
        return self.get_username()


class UserProfile(TimeStampedModel):

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="profile")


class Group(AbstractOrganization):
    class Meta:
        verbose_name = _("group")
        verbose_name_plural = _("groups")


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


class GroupOwner(AbstractOrganizationOwner):
    class Meta:
        verbose_name = _("network admin")
        verbose_name_plural = _("network admins")
