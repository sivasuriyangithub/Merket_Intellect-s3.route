from rest_framework import viewsets

from whoweb.users.models import Seat
from whoweb.contrib.rest_framework.permissions import IsSuperUser
from .models import WKPlan
from .serializers import PlanSerializer, AdminBillingSeatSerializer


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
