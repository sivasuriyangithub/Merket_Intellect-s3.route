import pytest

from whoweb.users.models import Group
from whoweb.users.tests.factories import NetworkFactory, UserFactory

pytestmark = pytest.mark.django_db


def test_get_or_add_user():
    network: Group = NetworkFactory()
    owner_user = UserFactory()

    owner_seat, created = network.get_or_add_user(owner_user)
    assert created
    assert network.users.count() == 1
    assert network.owner.user == owner_user
    assert owner_seat.user == owner_user

    owner_seat, created = network.get_or_add_user(owner_user)
    assert not created

    assert sorted(owner_user.groups.all(), key=lambda g: g.pk) == sorted(
        set(
            network.default_permission_groups + network.default_admin_permission_groups
        ),
        key=lambda g: g.pk,
    )

    user = UserFactory()

    seat, created = network.get_or_add_user(user)
    assert network.users.count() == 2
    assert network.owner.user == owner_user
    assert seat.user == user

    assert sorted(user.groups.all(), key=lambda g: g.pk) == sorted(
        network.default_permission_groups, key=lambda g: g.pk
    )


def test_remove_user():
    network: Group = NetworkFactory()
    owner_user = UserFactory()
    user = UserFactory()
    network.get_or_add_user(owner_user)
    network.get_or_add_user(user)
    assert network.users.count() == 2
    assert user.groups.all().count() == len(network.default_permission_groups)
    network.remove_user(user)
    assert user.groups.all().count() == 0


def test_change_owner():
    network: Group = NetworkFactory()
    owner_user = UserFactory()
    user = UserFactory()
    network.get_or_add_user(owner_user)
    seat, created = network.get_or_add_user(user)
    assert network.owner.user == owner_user
    assert network.users.count() == 2

    assert owner_user.groups.count() == len(
        set(network.default_permission_groups + network.default_admin_permission_groups)
    )
    assert user.groups.all().count() == len(network.default_permission_groups)

    network.change_owner(new_owner=seat)

    assert user.groups.all().count() == len(
        set(network.default_permission_groups + network.default_admin_permission_groups)
    )
    assert owner_user.groups.all().count() == len(network.default_permission_groups)
