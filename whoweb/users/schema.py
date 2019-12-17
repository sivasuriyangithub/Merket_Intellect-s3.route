import graphene
from django.contrib.auth import get_user_model
from graphene import relay
from graphene_django import DjangoConnectionField
from graphene_django.filter import DjangoFilterConnectionField
from rest_framework_guardian.filters import ObjectPermissionsFilter

from whoweb.contrib.graphene_django.types import GuardedObjectType
from whoweb.contrib.rest_framework.permissions import IsSuperUser, ObjectPermissions
from whoweb.users.models import UserProfile, Group, Seat, OrganizationCredentials

User = get_user_model()


class UserNode(GuardedObjectType):
    class Meta:
        model = User
        fields = ("username",)
        filter_fields = {"username": ["exact", "icontains", "istartswith"]}
        interfaces = (relay.Node,)
        permission_classes = [IsSuperUser | ObjectPermissions]
        filter_backends = (ObjectPermissionsFilter,)


class UserProfileNode(GuardedObjectType):
    class Meta:
        model = UserProfile
        filter_fields = ["user"]
        interfaces = (relay.Node,)
        permission_classes = [IsSuperUser | ObjectPermissions]
        filter_backends = (ObjectPermissionsFilter,)


class NetworkNode(GuardedObjectType):
    class Meta:
        model = Group
        filter_fields = {
            "slug": ["exact", "icontains", "istartswith"],
            "name": ["exact", "icontains", "istartswith"],
        }
        interfaces = (relay.Node,)
        permission_classes = [IsSuperUser | ObjectPermissions]
        filter_backends = (ObjectPermissionsFilter,)


class SeatNode(GuardedObjectType):
    class Meta:
        model = Seat
        filter_fields = {
            "display_name": ["exact", "icontains", "istartswith"],
            "user": ["exact"],
        }
        interfaces = (relay.Node,)
        permission_classes = [IsSuperUser | ObjectPermissions]
        filter_backends = (ObjectPermissionsFilter,)


class DeveloperKeyNode(GuardedObjectType):
    class Meta:
        model = OrganizationCredentials
        fields = ("key", "secret", "test_key", "group", "created", "created_by")
        interfaces = (relay.Node,)
        permission_classes = [IsSuperUser | ObjectPermissions]
        filter_backends = (ObjectPermissionsFilter,)


class Query(graphene.ObjectType):
    user = relay.Node.Field(UserNode)
    users = DjangoFilterConnectionField(UserNode)
    user_profiles = DjangoFilterConnectionField(UserProfileNode)
    networks = DjangoFilterConnectionField(NetworkNode)
    seats = DjangoFilterConnectionField(SeatNode)
    developer_keys = DjangoConnectionField(DeveloperKeyNode)
