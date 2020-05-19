from datetime import datetime

from django.utils.timezone import now
from djstripe.enums import SubscriptionStatus
from djstripe.models import Customer
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import BillingAccount
from ..serializers import AddPaymentSourceSerializer


class PaymentSourceAPIView(APIView):
    # TODO: user passes test Can Edit Customer
    def post(self, request, **kwargs):
        serializer = AddPaymentSourceSerializer(
            data=request.data, context={"request": request}
        )

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        billing_account: BillingAccount = serializer.validated_data["billing_account"]
        customer, _created = Customer.get_or_create(subscriber=billing_account)
        customer.add_card(serializer.validated_data["stripe_token"])

        if subscription := customer.subscription:
            if (
                subscription.status == SubscriptionStatus.trialing
                and subscription.trial_end > now()
            ):
                subscription.update(trial_end="now")
            elif subscription.status == SubscriptionStatus.unpaid:
                for invoice in customer.invoices:
                    if (
                        datetime.utcfromtimestamp(invoice.period_end)
                        < datetime.utcnow()
                        and invoice.amount_remaining > 0
                        and not invoice.forgiven
                    ):
                        stripe_invoice = invoice.api_retrieve()
                        updated_stripe_invoice = stripe_invoice.pay(forgive=True)
                        type(stripe_invoice).sync_from_stripe_data(
                            updated_stripe_invoice
                        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)
