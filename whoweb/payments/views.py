import logging

from djstripe.contrib.rest_framework.views import (
    SubscriptionRestView as DJStripeSubscriptionRestView,
)
from djstripe.models import Customer, Subscription, Plan
from djstripe.settings import subscriber_request_callback
from rest_framework import viewsets, status
from rest_framework.response import Response

from whoweb.users.models import Seat
from whoweb.contrib.rest_framework.permissions import IsSuperUser
from .models import WKPlan, WKPlanPreset
from .serializers import (
    PlanSerializer,
    AdminBillingSeatSerializer,
    CreateSubscriptionSerializer,
    UpdateSubscriptionSerializer,
)

logger = logging.getLogger(__name__)


class PlanViewSet(viewsets.ModelViewSet):
    lookup_field = "public_id"
    queryset = WKPlan.objects.all()
    serializer_class = PlanSerializer
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

        try:
            customer, _created = Customer.get_or_create(
                subscriber=subscriber_request_callback(self.request)
            )
            customer.add_card(serializer.data["stripe_token"])

            valid_items = self.get_valid_items(serializer)
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
        except Exception as e:
            logger.exception(e)
            return Response(
                "Something went wrong processing the payment.",
                status=status.HTTP_400_BAD_REQUEST,
            )

    def patch(self, request, **kwargs):
        serializer = UpdateSubscriptionSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            customer, _created = Customer.get_or_create(
                subscriber=subscriber_request_callback(self.request)
            )

            valid_items = self.get_valid_items(serializer)

            subscription = customer.subscription

            stripe_subscription = subscription.api_retrieve()
            setattr(stripe_subscription, "items", valid_items)
            Subscription.sync_from_stripe_data(stripe_subscription.save())

            charge_immediately = serializer.data.get("charge_immediately")
            if charge_immediately is None:
                charge_immediately = False
            if charge_immediately:
                customer.send_invoice()
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception(e)
            return Response(
                "Something went wrong processing the payment.",
                status=status.HTTP_400_BAD_REQUEST,
            )

    def get_valid_items(self, serializer):
        plan_preset = WKPlanPreset.objects.get(public_id=serializer.data["plan"])
        valid_plans = plan_preset.stripe_plans.all().values_list("id", flat=True)
        valid_items = []
        for plan_id, quantity in serializer.data["items"].items():
            if plan_id in valid_plans:
                valid_items.append({"plan": plan_id, "quantity": quantity})
        return valid_items
