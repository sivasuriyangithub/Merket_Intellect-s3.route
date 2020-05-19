from rest_framework import viewsets

from whoweb.contrib.rest_framework.permissions import IsSuperUser
from whoweb.users.models import Seat
from ..serializers import (
    AdminBillingSeatSerializer,
    AdminBillingAccountSerializer,
)


class AdminBillingSeatViewSet(viewsets.ModelViewSet):
    lookup_field = "public_id"
    queryset = Seat.objects.all()
    serializer_class = AdminBillingSeatSerializer
    permission_classes = [IsSuperUser]
    schema = None


class AdminBillingAccountViewSet(viewsets.ModelViewSet):
    lookup_field = "public_id"
    queryset = Seat.objects.all()
    serializer_class = AdminBillingAccountSerializer
    permission_classes = [IsSuperUser]
    schema = None
