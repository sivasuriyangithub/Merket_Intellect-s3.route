import logging
from datetime import datetime
from typing import Union

from django.contrib.auth.decorators import login_required
from djstripe.contrib.rest_framework.views import (
    SubscriptionRestView as DJStripeSubscriptionRestView,
)
from djstripe.enums import SubscriptionStatus
from djstripe.models import Customer, Subscription
from djstripe.settings import subscriber_request_callback
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.views import APIView

from whoweb.contrib.rest_framework.permissions import IsSuperUser
from whoweb.users.models import Seat
from .models import WKPlan, WKPlanPreset, BillingAccount, BillingAccountMember
from .serializers import (
    PlanSerializer,
    AdminBillingSeatSerializer,
    CreateSubscriptionSerializer,
    UpdateSubscriptionSerializer,
    BillingAccountSerializer,
    AddPaymentSourceSerializer,
    AdminBillingAccountSerializer,
    BillingAccountMemberSerializer,
)

logger = logging.getLogger(__name__)


class PlanViewSet(viewsets.ModelViewSet):
    lookup_field = "public_id"
    queryset = WKPlan.objects.all()
    serializer_class = PlanSerializer
    permission_classes = [IsSuperUser]


class BillingAccountViewSet(viewsets.ModelViewSet):
    lookup_field = "public_id"
    queryset = BillingAccount.objects.all()
    serializer_class = BillingAccountSerializer
    permission_classes = [IsSuperUser]


class BillingAccountMemberViewSet(viewsets.ModelViewSet):
    lookup_field = "public_id"
    queryset = BillingAccountMember.objects.all()
    serializer_class = BillingAccountMemberSerializer
    permission_classes = [IsSuperUser]


class AdminBillingSeatViewSet(viewsets.ModelViewSet):
    lookup_field = "public_id"
    queryset = Seat.objects.all()
    serializer_class = AdminBillingSeatSerializer
    permission_classes = [IsSuperUser]


class AdminBillingAccountViewSet(viewsets.ModelViewSet):
    lookup_field = "public_id"
    queryset = Seat.objects.all()
    serializer_class = AdminBillingAccountSerializer
    permission_classes = [IsSuperUser]


class AddPaymentSourceRestView(APIView):
    # TODO: user passes test Can Edit Customer
    @login_required
    def post(self, request, **kwargs):
        serializer = AddPaymentSourceSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        billing_account: BillingAccount = serializer.data["billing_account"]
        customer, _created = Customer.get_or_create(subscriber=billing_account)
        customer.add_card(serializer.data["stripe_token"])

        if subscription := customer.subscription:
            if (
                subscription.status == SubscriptionStatus.trialing
                and subscription.trial_end > datetime.utcnow()
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
        return Response(serializer.data, status=status.HTTP_200_OK)


class SubscriptionRestView(DJStripeSubscriptionRestView):
    @login_required
    def post(self, request, **kwargs):
        serializer = CreateSubscriptionSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        valid_items, plan_preset, total_credits = self.get_valid_items(serializer)
        wkplan = plan_preset.create()
        billing_account: BillingAccount = serializer.data["billing_account"]
        billing_account.update_plan(new_plan=wkplan, with_credits=total_credits)

        customer, _created = Customer.get_or_create(subscriber=billing_account)
        token = serializer.data.get("stripe_token")
        if token:
            customer.add_card(token)

        stripe_subscription = Subscription._api_create(
            items=valid_items, customer=customer.id
        )
        Subscription.sync_from_stripe_data(stripe_subscription)

        charge_immediately = serializer.data.get("charge_immediately")
        if charge_immediately is None or not token:
            charge_immediately = False
        if charge_immediately:
            customer.send_invoice()

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def patch(self, request, **kwargs):
        serializer = UpdateSubscriptionSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        customer, _created = Customer.get_or_create(
            subscriber=subscriber_request_callback(self.request)
        )
        token = serializer.data.get("stripe_token")
        if token:
            customer.add_card(token)

        valid_items, preset, total_credits = self.get_valid_items(serializer)

        subscription = customer.subscription
        stripe_subscription = subscription.api_retrieve()
        setattr(stripe_subscription, "items", valid_items)
        Subscription.sync_from_stripe_data(stripe_subscription.save())

        charge_immediately = serializer.data.get("charge_immediately")
        if charge_immediately is None or not token:
            charge_immediately = False
        if charge_immediately:
            customer.send_invoice()

        return Response(serializer.data, status=status.HTTP_200_OK)

    def get_valid_items(
        self,
        serializer: Union[CreateSubscriptionSerializer, UpdateSubscriptionSerializer],
    ) -> (dict, WKPlan):
        plan_preset = WKPlanPreset.objects.get(public_id=serializer.data["plan"])
        valid_plans = plan_preset.stripe_plans.all().values_list("id", flat=True)
        valid_items = []
        total_credits = 0
        for plan_id, quantity in serializer.data["items"].items():
            if plan_id in valid_plans:
                total_credits += quantity
                valid_items.append({"plan": plan_id, "quantity": quantity})
        return valid_items, plan_preset, total_credits
