from django.contrib.auth import get_user_model
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, mixins
from rest_framework.viewsets import GenericViewSet
from whoweb.contrib.rest_framework.filters import ObjectPermissionsFilter

from whoweb.contrib.rest_framework.permissions import ObjectPermissions, IsSuperUser
from whoweb.users.models import Seat, DeveloperKey, Network, UserProfile
from whoweb.users.serializers import (
    SeatSerializer,
    DeveloperKeySerializer,
    NetworkSerializer,
    UserSerializer,
)

User = get_user_model()


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    lookup_field = "public_id"
    queryset = UserProfile.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsSuperUser | ObjectPermissions]
    filter_backends = [DjangoFilterBackend, ObjectPermissionsFilter]


class NetworkViewSet(viewsets.ReadOnlyModelViewSet):
    lookup_field = "public_id"
    queryset = Network.objects.all()
    serializer_class = NetworkSerializer
    permission_classes = [IsSuperUser | ObjectPermissions]
    filter_backends = [DjangoFilterBackend, ObjectPermissionsFilter]


class SeatViewSet(viewsets.ModelViewSet):
    lookup_field = "public_id"
    queryset = Seat.objects.all()
    serializer_class = SeatSerializer
    permission_classes = [IsSuperUser | ObjectPermissions]
    filter_backends = [DjangoFilterBackend, ObjectPermissionsFilter]


class DeveloperKeyViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
    GenericViewSet,
):
    lookup_field = "public_id"
    queryset = DeveloperKey.objects.all()
    serializer_class = DeveloperKeySerializer
    permission_classes = [IsSuperUser | ObjectPermissions]
    filter_backends = [DjangoFilterBackend, ObjectPermissionsFilter]
