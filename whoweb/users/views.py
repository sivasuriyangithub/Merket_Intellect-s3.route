from django.contrib.auth import get_user_model
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, mixins
from rest_framework.viewsets import GenericViewSet
from rest_framework_guardian.filters import ObjectPermissionsFilter

from whoweb.contrib.rest_framework.permissions import ObjectPermissions, IsSuperUser
from whoweb.users.models import Seat, OrganizationCredentials, Group
from whoweb.users.serializers import (
    SeatSerializer,
    OrganizationCredentialsSerializer,
    GroupSerializer,
)

User = get_user_model()


class NetworkViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [IsSuperUser | ObjectPermissions]
    filter_backends = [DjangoFilterBackend, ObjectPermissionsFilter]


class SeatViewSet(viewsets.ReadOnlyModelViewSet):
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
    queryset = OrganizationCredentials.objects.all()
    serializer_class = OrganizationCredentialsSerializer
    permission_classes = [IsSuperUser | ObjectPermissions]
    filter_backends = [DjangoFilterBackend, ObjectPermissionsFilter]
