from django.contrib.auth import get_user_model
from rest_framework import viewsets, mixins
from rest_framework.viewsets import GenericViewSet
from rest_framework_extensions.mixins import NestedViewSetMixin
from rest_framework_guardian.filters import ObjectPermissionsFilter

from whoweb.contrib.rest_framework.permissions import ObjectPermissions, IsSuperUser
from whoweb.users.models import Seat, OrganizationCredentials
from whoweb.users.serializers import SeatSerializer, OrganizationCredentialsSerializer

User = get_user_model()


class SeatViewSet(viewsets.ModelViewSet):
    queryset = Seat.objects.none()
    serializer_class = SeatSerializer


class OrgCredentialObjectPermissions(ObjectPermissions):
    def has_object_permission(self, request, view, obj):
        if super().has_object_permission(request, view, obj):
            return request.user.has_perm("add_credentials", obj.group)
        return False


class OrganizationCredentialsSerializerViewSet(
    NestedViewSetMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
    GenericViewSet,
):
    queryset = OrganizationCredentials.objects.all()
    serializer_class = OrganizationCredentialsSerializer
    permission_classes = [IsSuperUser | ObjectPermissions]
    filter_backends = [ObjectPermissionsFilter]

    # def get_queryset(self):
    #     user = self.request.user
    #     return get_objects_for_user(user)
    #     return super().get_queryset().filter()
