from djstripe.contrib.rest_framework.views import (
    SubscriptionRestView as DJStripeSubscriptionRestView,
)
from djstripe.models import Customer
from djstripe.settings import subscriber_request_callback
from rest_framework import viewsets, status
from rest_framework.response import Response

from whoweb.users.models import Seat
from whoweb.contrib.rest_framework.permissions import IsSuperUser
from .models import WKPlan
from .serializers import (
    PlanSerializer,
    AdminBillingSeatSerializer,
    CreateSubscriptionSerializer,
)


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

        if serializer.is_valid():
            try:
                customer, _created = Customer.get_or_create(
                    subscriber=subscriber_request_callback(self.request)
                )
                customer.add_card(serializer.data["stripe_token"])
                charge_immediately = serializer.data.get("charge_immediately")
                if charge_immediately is None:
                    charge_immediately = True
                for plan in serializer.data["plans"]:
                    customer.subscribe(plan, charge_immediately)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            except Exception:
                return Response(
                    "Something went wrong processing the payment.",
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
