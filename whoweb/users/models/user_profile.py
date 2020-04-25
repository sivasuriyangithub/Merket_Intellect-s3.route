from allauth.account.models import EmailAddress
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _
from guardian.mixins import GuardianUserMixin
from model_utils.models import TimeStampedModel

from whoweb.contrib.fields import ObscureIdMixin


class UserProfile(ObscureIdMixin, TimeStampedModel):
    user = models.OneToOneField(
        "User", on_delete=models.CASCADE, related_name="profile"
    )

    @classmethod
    def get_or_create(cls, email, username=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        email = User.objects.normalize_email(email)
        username = User.normalize_username(username or email)
        extra_fields["username"] = username
        user, created = User.objects.get_or_create(email=email, defaults=extra_fields)
        if created:
            user.set_password(password)
            user.save()
        EmailAddress.objects.get_or_create(
            user=user,
            email__iexact=email,
            defaults={"email": email, "verified": True, "primary": True},
        )
        return cls.objects.get_or_create(user=user)

    @cached_property
    def username(self):
        return self.user.username


# WARN: See docstring.
class User(GuardianUserMixin, AbstractUser):
    """
    Generally, only auth or permissions related fields should exist on this model.
    See UserProfile for custom fields that should be one-to-one with a user.
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
