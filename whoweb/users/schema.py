import graphene
from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from graphene import relay
from graphene_django import DjangoConnectionField
from graphene_django.filter import DjangoFilterConnectionField
from graphql_jwt.decorators import login_required

from whoweb.contrib.graphene_django.types import GuardedObjectType, ObscureIdNode
from whoweb.contrib.rest_framework.filters import ObjectPermissionsFilter
from whoweb.contrib.rest_framework.permissions import (
    IsSuperUser,
    ObjectPermissions,
    ObjectPassesTest,
)
from whoweb.users.models import UserProfile, Group, Seat, DeveloperKey
from .permissions import NetworkSeatPermissionsFilter

User = get_user_model()


def member_of_network(viewer: User, profile: UserProfile):
    return not set(viewer.users_group.all().values_list("pk", flat=True)).isdisjoint(
        profile.user.users_group.all().values_list("pk", flat=True)
    )


class EmailAddressType(GuardedObjectType):
    class Meta:
        model = EmailAddress
        fields = ("email", "verified", "primary")
        permission_classes = [IsSuperUser | ObjectPermissions]
        interfaces = (relay.Node,)
        filter_backends = (ObjectPermissionsFilter,)


class UserNode(GuardedObjectType):
    emails = DjangoConnectionField(EmailAddressType)
    username = graphene.String()
    seats = DjangoConnectionField("whoweb.users.schema.SeatNode")
    first_name = graphene.String(resolver=lambda x, i: x.user.first_name)
    last_name = graphene.String(resolver=lambda x, i: x.user.last_name)

    class Meta:
        model = UserProfile
        fields = ("created",)
        interfaces = (ObscureIdNode,)
        permission_classes = [
            ObjectPassesTest(member_of_network) | IsSuperUser | ObjectPermissions
        ]
        filter_backends = (ObjectPermissionsFilter,)

    def resolve_emails(self, info):
        return EmailAddress.objects.filter(user=self.user)

    def resolve_seats(self, info):
        return Seat.objects.filter(user=self.user)


class NetworkNode(GuardedObjectType):
    seats = DjangoFilterConnectionField(
        "whoweb.users.schema.SeatNode", source="organization_users"
    )

    class Meta:
        model = Group
        fields = (
            "name",
            "slug",
            "created",
            "modified",
            "seats",
            "credentials",
        )
        filter_fields = {
            "id": ["exact"],
            "slug": ["exact", "icontains", "istartswith"],
            "name": ["exact", "icontains", "istartswith"],
        }
        interfaces = (ObscureIdNode,)
        permission_classes = [IsSuperUser | ObjectPermissions]
        filter_backends = (ObjectPermissionsFilter,)


class SeatNode(GuardedObjectType):
    network = graphene.Field(NetworkNode, source="organization")
    user = graphene.Field(
        UserNode
    )  # TODO: ensure we want view_seat to incorporate view_user, or verify obj perm chk

    class Meta:
        model = Seat
        filter_fields = {
            "display_name": ["exact", "icontains", "istartswith"],
            "user": ["exact"],
            "user__email": ["exact", "icontains", "istartswith"],
            "title": ["exact", "icontains", "istartswith"],
        }
        fields = (
            "title",
            "created",
            "modified",
            "is_admin",
            "display_name",
            "credentials",
            "billing",
        )
        interfaces = (ObscureIdNode,)
        permission_classes = [IsSuperUser | ObjectPermissions]
        filter_backends = (ObjectPermissionsFilter | NetworkSeatPermissionsFilter,)


class DeveloperKeyNode(GuardedObjectType):
    class Meta:
        model = DeveloperKey
        fields = ("key", "secret", "test_key", "network", "created", "created_by")
        interfaces = (ObscureIdNode,)
        permission_classes = [IsSuperUser | ObjectPermissions]
        filter_backends = (ObjectPermissionsFilter,)


class Query(graphene.ObjectType):
    users = DjangoConnectionField(UserNode)
    networks = DjangoFilterConnectionField(NetworkNode)
    seats = DjangoFilterConnectionField(SeatNode)
    developer_keys = DjangoConnectionField(DeveloperKeyNode)
    me = graphene.Field(UserNode)

    def resolve_me(self, info):
        return UserNode.get_node(info, info.context.user.profile.public_id)
