import logging
from typing import Union

from djstripe.contrib.rest_framework.views import (
    SubscriptionRestView as DJStripeSubscriptionRestView,
)
from djstripe.models import Customer, Subscription
from djstripe.settings import subscriber_request_callback
from rest_framework import viewsets, status
from rest_framework.exceptions import APIException
from rest_framework.response import Response

from whoweb.contrib.rest_framework.permissions import IsSuperUser
from whoweb.users.models import Seat
from .models import WKPlan, WKPlanPreset, BillingAccount
from .serializers import (
    PlanSerializer,
    AdminBillingSeatSerializer,
    CreateSubscriptionSerializer,
    UpdateSubscriptionSerializer,
    BillingAccountSerializer,
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


class AdminBillingSeatViewSet(viewsets.ModelViewSet):
    lookup_field = "public_id"
    queryset = Seat.objects.all()
    serializer_class = AdminBillingSeatSerializer
    permission_classes = [IsSuperUser]


class SubscriptionRestView(DJStripeSubscriptionRestView):
    def post(self, request, **kwargs):
        serializer = CreateSubscriptionSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        valid_items, plan_preset = self.get_valid_items(serializer)
        wkplan = plan_preset.create()
        billing_account: BillingAccount = serializer.data["billing_account"]
        billing_account.update_plan(new_plan=wkplan)

        customer, _created = Customer.get_or_create(subscriber=billing_account)
        customer.add_card(serializer.data["stripe_token"])

        stripe_subscription = Subscription._api_create(
            items=valid_items, customer=customer.id
        )
        Subscription.sync_from_stripe_data(stripe_subscription)

        charge_immediately = serializer.data.get("charge_immediately")
        if charge_immediately is None:
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

        valid_items, preset = self.get_valid_items(serializer)

        subscription = customer.subscription
        stripe_subscription = subscription.api_retrieve()
        setattr(stripe_subscription, "items", valid_items)
        Subscription.sync_from_stripe_data(stripe_subscription.save())

        charge_immediately = serializer.data.get("charge_immediately")
        if charge_immediately is None:
            charge_immediately = False
        if charge_immediately:
            customer.send_invoice()
        billing_account: BillingAccount = serializer.data["billing_account"]
        plan = billing_account.plan
        if plan and not all(
            [
                preset.credits_per_enrich == plan.credits_per_enrich,
                preset.credits_per_work_email == plan.credits_per_work_email,
                preset.credits_per_personal_email == plan.credits_per_personal_email,
                preset.credits_per_phone == plan.credits_per_phone,
            ]
        ):
            wkplan = preset.create()
            billing_account.update_plan(new_plan=wkplan)

        return Response(serializer.data, status=status.HTTP_200_OK)

    def get_valid_items(
        self,
        serializer: Union[CreateSubscriptionSerializer, UpdateSubscriptionSerializer],
    ) -> (dict, WKPlan):
        plan_preset = WKPlanPreset.objects.get(public_id=serializer.data["plan"])
        valid_plans = plan_preset.stripe_plans.all().values_list("id", flat=True)
        valid_items = []
        for plan_id, quantity in serializer.data["items"].items():
            if plan_id in valid_plans:
                valid_items.append({"plan": plan_id, "quantity": quantity})
        return valid_items, plan_preset
