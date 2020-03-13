from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.exceptions import APIException


class SubscriptionError(Exception):
    pass


class PaymentRequired(APIException):
    status_code = status.HTTP_402_PAYMENT_REQUIRED
    default_detail = _("You do not have sufficient credits to perform this action.")
    default_code = "payment_required"
