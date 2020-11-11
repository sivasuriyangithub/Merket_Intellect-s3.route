import django_filters
import graphene
from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django_filters.rest_framework import FilterSet
from graphene import relay
from graphene_django import DjangoConnectionField
from graphene_django.filter import DjangoFilterConnectionField, GlobalIDFilter
from graphql_jwt.decorators import login_required

from whoweb.contrib.graphene_django.types import GuardedObjectType, ObscureIdNode
from whoweb.contrib.rest_framework.filters import (
    ObjectPermissionsFilter,
    ObscureIdFilterSet,
    id_filterset_class_for,
)
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
        filterset_class = id_filterset_class_for(UserProfile)
        interfaces = (ObscureIdNode,)
        permission_classes = [
            ObjectPassesTest(member_of_network) | IsSuperUser | ObjectPermissions
        ]
        filter_backends = (ObjectPermissionsFilter,)

    def resolve_emails(self, info):
        return EmailAddress.objects.filter(user=self.user)

    def resolve_seats(self, info):
        return Seat.objects.filter(user=self.user)


class NetworkFilterSet(ObscureIdFilterSet):
    slug = django_filters.CharFilter()
    slug_contains = django_filters.CharFilter("slug", lookup_expr="icontains")
    name = django_filters.CharFilter()
    name_contains = django_filters.CharFilter("name", lookup_expr="icontains")

    class Meta:
        model = Group
        fields = ("id", "slug", "name")


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
        filterset_class = NetworkFilterSet
        interfaces = (ObscureIdNode,)
        permission_classes = [IsSuperUser | ObjectPermissions]
        filter_backends = (ObjectPermissionsFilter,)


class SeatFilterSet(ObscureIdFilterSet):
    user = GlobalIDFilter(field_name="user__profile__public_id")
    user_email = django_filters.CharFilter(field_name="user__email")
    username = django_filters.CharFilter(field_name="user__username")

    class Meta:
        model = Seat
        fields = (
            "id",
            "user",
        )


class SeatNode(GuardedObjectType):
    network = graphene.Field(NetworkNode, source="organization")
    user = graphene.Field(
        UserNode, resolver=lambda x, y: x.user.profile
    )  # TODO: ensure we want view_seat to incorporate view_user, or verify obj perm chk

    class Meta:
        model = Seat
        filterset_class = SeatFilterSet
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
