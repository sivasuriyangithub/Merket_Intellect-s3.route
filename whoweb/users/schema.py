import graphene
from django.contrib.auth import get_user_model
from graphene import relay
from graphene_django.filter import DjangoFilterConnectionField

from whoweb.contrib.graphene_django.types import ProtectedDjangoObjectType
from whoweb.users.models import UserProfile, Group, Seat

User = get_user_model()


class UserNode(ProtectedDjangoObjectType):
    class Meta:
        model = User
        fields = ("username",)
        filter_fields = {
            "username": ["exact", "icontains", "istartswith"],
            "id": ["exact"],
        }
        interfaces = (relay.Node,)


class UserProfileNode(ProtectedDjangoObjectType):
    class Meta:
        model = UserProfile
        filter_fields = ["user"]
        interfaces = (relay.Node,)


class GroupNode(ProtectedDjangoObjectType):
    class Meta:
        model = Group
        filter_fields = {
            "slug": ["exact", "icontains", "istartswith"],
            "name": ["exact", "icontains", "istartswith"],
        }
        interfaces = (relay.Node,)


class SeatNode(ProtectedDjangoObjectType):
    class Meta:
        model = Seat

        filter_fields = {
            "display_name": ["exact", "icontains", "istartswith"],
            "user": ["exact"],
        }
        interfaces = (relay.Node,)


class Query(graphene.ObjectType):
    user = relay.Node.Field(UserNode)
    users = DjangoFilterConnectionField(UserNode)
    user_profiles = DjangoFilterConnectionField(UserProfileNode)
    groups = DjangoFilterConnectionField(GroupNode)
    seats = DjangoFilterConnectionField(SeatNode)
