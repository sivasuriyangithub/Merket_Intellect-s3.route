from datetime import datetime, timedelta
from typing import Union

from IPython.utils.tz import utcnow
from django.db.models import Q
from django.utils.timezone import now
from djstripe.enums import SubscriptionStatus
from djstripe.models import Customer, Subscription
from djstripe.settings import CANCELLATION_AT_PERIOD_END
from django.core.exceptions import ValidationError as CoreValidationError

from rest_framework import status
from rest_framework.exceptions import ValidationError, MethodNotAllowed
from rest_framework.response import Response
from rest_framework.views import APIView

from whoweb.core.utils import IdempotentRequest
from ..models import WKPlan, WKPlanPreset, BillingAccount, MultiPlanCustomer
from ..serializers import (
    CreateSubscriptionSerializer,
    UpdateSubscriptionSerializer,
    AddPaymentSourceSerializer,
    SubscriptionSerializer,
    CreditChargeSerializer,
)


class AddPaymentSourceRestView(APIView):
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


class SubscriptionRestView(APIView):
    def post(self, request, **kwargs):
        serializer = CreateSubscriptionSerializer(
            data=request.data, context={"request": request}
        )

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        valid_items, plan_preset, total_credits = self._get_valid_items(serializer)
        billing_account: BillingAccount = serializer.validated_data["billing_account"]
        customer = billing_account.customer
        if customer.valid_subscriptions:
            raise MethodNotAllowed(
                method="POST", detail="Customer already subscribed, use PATCH instead."
            )
        token = serializer.validated_data.get("stripe_token")
        trial_days = serializer.validated_data.get("trial_days", None)

        if trial_days is None:
            trial_days = plan_preset.trial_days_allowed
        if trial_days == 0 or token:
            trial_end = "now"
        elif trial_days > plan_preset.trial_days_allowed:
            raise ValidationError(
                f"Invalid number of trial days. Must be less than {plan_preset.trial_days_allowed}."
            )
        else:
            trial_end = str(round((utcnow() + timedelta(days=trial_days)).timestamp()))

        if token:
            customer.add_card(token)

        subscription = customer.subscribe(
            items=valid_items,
            trial_end=trial_end,
            charge_immediately=serializer.validated_data.get(
                "charge_immediately", False
            ),
        )

        if subscription.status == SubscriptionStatus.trialing:
            with_credits = min(total_credits, 1000)
        else:
            with_credits = total_credits
        billing_account.update_plan(
            initiated_by=self.request.user,
            new_plan=plan_preset.create(),
            with_credits=with_credits,
        )
        # TODO: another endpoint for managing pool
        billing_account.set_pool_for_all_members()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def patch(self, request, **kwargs):
        serializer = UpdateSubscriptionSerializer(
            data=request.data, context={"request": request}
        )

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        billing_account: BillingAccount = serializer.validated_data["billing_account"]
        customer = billing_account.customer
        token = serializer.validated_data.get("stripe_token")
        if token:
            customer.add_card(token)

        valid_items, plan_preset, total_credits = self._get_valid_items(serializer)

        subscription = customer.subscription.update(
            items=valid_items, trial_end="now" if token else None
        )

        if subscription.status == SubscriptionStatus.trialing:
            with_credits = min(total_credits, 1000)
        else:
            with_credits = total_credits
        billing_account.update_plan(
            initiated_by=self.request.user,
            new_plan=plan_preset.create(),
            with_credits=with_credits,
        )
        # TODO: another endpoint for managing pool
        billing_account.set_pool_for_all_members()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def _get_valid_items(
        self,
        serializer: Union[CreateSubscriptionSerializer, UpdateSubscriptionSerializer],
    ) -> (dict, WKPlan, int):
        tag_or_public_id = serializer.validated_data.get("plan")
        plan_preset = WKPlanPreset.objects.filter(
            Q(tag=tag_or_public_id) | Q(public_id=tag_or_public_id)
        ).first()
        if not plan_preset:
            raise ValidationError("A valid plan id or tag must be specified.")
        try:
            valid_items, total_credits = plan_preset.validate_items(
                serializer.validated_data["items"]
            )
            return valid_items, plan_preset, total_credits
        except CoreValidationError as e:
            raise ValidationError(e)

    def get(self, request, billing_account_id, **kwargs):
        """
        Return the customer's valid subscriptions.

        Returns with status code 200.
        """
        try:
            billing_account = BillingAccount.objects.get(pk=billing_account_id)
        except ValueError:
            billing_account = BillingAccount.objects.get(public_id=billing_account_id)
        customer, _created = Customer.get_or_create(subscriber=billing_account)
        serializer = SubscriptionSerializer(customer.subscription)
        return Response(serializer.data)

    def delete(self, request, billing_account_id, **kwargs):
        """
        Mark the customers current subscription as canceled.

        Returns with status code 204.
        """
        try:
            billing_account = BillingAccount.objects.get(pk=billing_account_id)
        except ValueError:
            billing_account = BillingAccount.objects.get(public_id=billing_account_id)

        customer, _created = Customer.get_or_create(subscriber=billing_account)
        customer.subscription.cancel(at_period_end=CANCELLATION_AT_PERIOD_END)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CreditChargeRestView(APIView):
    def post(self, request, **kwargs):
        serializer = CreditChargeSerializer(
            data=request.data, context={"request": request}
        )

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        billing_account: BillingAccount = serializer.validated_data.pop(
            "billing_account"
        )

        idempotency = IdempotentRequest(request)
        if idempotency.is_idempotent():
            try:
                success = billing_account.consume_credits(**serializer.validated_data)
            except:
                idempotency.rewind()
                raise
        else:
            success = True
        if success:
            return Response(serializer.data, status=status.HTTP_202_ACCEPTED)
        else:
            return Response(serializer.data, status=status.HTTP_402_PAYMENT_REQUIRED)
