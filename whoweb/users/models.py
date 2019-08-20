from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import CharField
from django.utils.translation import ugettext_lazy as _
from model_utils.models import TimeStampedModel


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


class UserProfile(TimeStampedModel):

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="profile")
    name = CharField(_("Name of User"), blank=True, max_length=255)
