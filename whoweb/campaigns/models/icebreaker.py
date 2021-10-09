from django.db import models
from django.utils.safestring import mark_safe
from model_utils.models import SoftDeletableModel

from whoweb.campaigns.jinja_filters import environment
from whoweb.payments.models import BillingAccountMember
from whoweb.contrib.fields import ObscureIdMixin


class IcebreakerTemplate(ObscureIdMixin, SoftDeletableModel):

    billing_seat = models.ForeignKey(
        BillingAccountMember, on_delete=models.CASCADE, null=True, blank=True
    )
    text = models.TextField(
        help_text=mark_safe(
            '<a href="https://jinja.palletsprojects.com/en/3.0.x/templates/" target=_blank>Documentation</a>'
        ),
        default="",
    )
    is_global_default = models.NullBooleanField(default=None, unique=True)

    def get_template(self):
        return environment().from_string(self.text)

    def save(self, *args, **kwargs):
        if self.is_global_default is False:
            self.is_the_chosen_one = None
        super(IcebreakerTemplate, self).save(*args, **kwargs)
