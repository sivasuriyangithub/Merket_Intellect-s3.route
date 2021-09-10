from django.db import models
from model_utils.models import SoftDeletableModel

from whoweb.payments.models import BillingAccountMember
from whoweb.contrib.fields import ObscureIdMixin


class IcebreakerTemplate(ObscureIdMixin, SoftDeletableModel):

    billing_seat = models.ForeignKey(
        BillingAccountMember, on_delete=models.CASCADE, null=True, blank=True
    )
    text = models.TextField()

    @property
    def is_global(self):
        return self.billing_seat is None
