from django.contrib.auth import get_user_model
from rest_framework import viewsets

from whoweb.users.models import Seat
from whoweb.users.serializers import SeatSerializer

User = get_user_model()


class SeatViewSet(viewsets.ModelViewSet):

    queryset = Seat.objects.all()
    serializer_class = SeatSerializer
