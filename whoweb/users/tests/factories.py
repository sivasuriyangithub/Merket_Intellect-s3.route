from typing import Any, Sequence
from uuid import uuid4

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group as PermissionGroup
from factory import (
    Faker,
    post_generation,
    SubFactory,
    SelfAttribute,
    RelatedFactory,
)
from factory.django import DjangoModelFactory

from whoweb.users.models import Group, GroupOwner, Seat, UserProfile


class EmailAddressFactory(DjangoModelFactory):
    user = SubFactory("whoweb.users.tests.factories.UserFactory")
    email = Faker("email")
    verified = True
    primary = True

    class Meta:
        model = EmailAddress


class UserProfileFactory(DjangoModelFactory):

    xperweb_id = Faker("user_name")

    class Meta:
        model = UserProfile


class UserFactory(DjangoModelFactory):
    username = Faker("user_name")
    profile = RelatedFactory(UserProfileFactory, "user")
    email = Faker("email")
    emails = RelatedFactory(EmailAddressFactory, "user")

    @post_generation
    def password(self, create: bool, extracted: Sequence[Any], **kwargs):
        password = str(uuid4())
        self.set_password(password)

    class Meta:
        model = get_user_model()
        django_get_or_create = ["username"]


class GroupFactory(DjangoModelFactory):
    name = Faker("slug")

    class Meta:
        model = PermissionGroup


class NetworkFactory(DjangoModelFactory):
    name = Faker("company")

    class Meta:
        model = Group


class SeatFactory(DjangoModelFactory):
    user = SubFactory(UserFactory)
    organization = SubFactory(NetworkFactory)
    display_name = Faker("user_name")

    class Meta:
        model = Seat


class NetworkOwnerFactory(DjangoModelFactory):
    organization_user = SubFactory(SeatFactory)
    organization = SelfAttribute("organization_user.organization")

    class Meta:
        model = GroupOwner
