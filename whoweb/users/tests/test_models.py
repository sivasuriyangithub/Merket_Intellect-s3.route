import pytest

from whoweb.users.models import Group
from whoweb.users.tests.factories import GroupFactory, UserFactory

pytestmark = pytest.mark.django_db


def test_get_or_add_user():
    group: Group = GroupFactory()
    owner_user = UserFactory()

    owner_seat, created = group.get_or_add_user(owner_user)
    assert created
    assert group.users.count() == 1
    assert group.owner.user == owner_user
    assert owner_seat.user == owner_user

    owner_seat, created = group.get_or_add_user(owner_user)
    assert not created

    assert sorted(owner_user.groups.all(), key=lambda g: g.pk) == sorted(
        group.default_permission_groups + group.default_admin_permission_groups,
        key=lambda g: g.pk,
    )

    user = UserFactory()

    seat, created = group.get_or_add_user(user)
    assert group.users.count() == 2
    assert group.owner.user == owner_user
    assert seat.user == user

    assert sorted(user.groups.all(), key=lambda g: g.pk) == sorted(
        group.default_permission_groups, key=lambda g: g.pk
    )


def test_remove_user():
    group: Group = GroupFactory()
    owner_user = UserFactory()
    user = UserFactory()
    group.get_or_add_user(owner_user)
    group.get_or_add_user(user)
    assert group.users.count() == 2
    assert user.groups.all().count() == len(group.default_permission_groups)
    group.remove_user(user)
    assert user.groups.all().count() == 0


def test_change_owner():
    group: Group = GroupFactory()
    owner_user = UserFactory()
    user = UserFactory()
    group.get_or_add_user(owner_user)
    seat, created = group.get_or_add_user(user)
    assert group.owner.user == owner_user
    assert group.users.count() == 2

    assert owner_user.groups.count() == len(
        group.default_permission_groups + group.default_admin_permission_groups
    )
    assert user.groups.all().count() == len(group.default_permission_groups)

    group.change_owner(new_owner=seat)

    assert user.groups.all().count() == len(
        group.default_permission_groups + group.default_admin_permission_groups
    )
    assert owner_user.groups.all().count() == len(group.default_permission_groups)
