from django.contrib.auth.models import Group
from django.db import models
from django.db.transaction import atomic
from django.utils.translation import ugettext_lazy as _
from organizations.signals import user_added


class PermissionsAbstractOrganization(models.Model):
    class Meta:
        abstract = True
        verbose_name = _("organization")
        verbose_name_plural = _("organizations")

    @property
    def permissions_scope(self):
        return f"{self.__class__.__name__.lower()}.{self.slug}"

    def get_or_create_auth_group(self, name):

        return Group.objects.get_or_create(name=f"{self.permissions_scope}:{name}")

    @property
    def default_admin_permission_groups(self):
        raise NotImplemented

    @property
    def default_permission_groups(self):
        raise NotImplemented

    @atomic
    def get_or_add_user(self, user, **kwargs):
        """
        Same as super(), but
         - allows for additional keyword user defaults
         - adds default and owner permission groups
        """

        users_count = self.users.all().count()
        kwargs.setdefault("is_admin", users_count == 0)

        org_user, created = self._org_user_model.objects.get_or_create(
            organization=self, user=user, defaults=kwargs
        )
        if users_count == 0:
            self._org_owner_model.objects.create(
                organization=self, organization_user=org_user
            )
            if created:
                user.groups.add(*self.default_admin_permission_groups)

        if created:
            # User added signal
            user_added.send(sender=self, user=user)
            user.groups.add(*self.default_permission_groups)
        return org_user, created

    @atomic
    def change_owner(self, new_owner):
        from_user = self.owner.organization_user.user
        admin_groups = list(
            from_user.groups.filter(name__startswith=f"{self.permissions_scope}:")
        )
        from_user.groups.remove(*admin_groups)
        from_user.groups.add(*self.default_permission_groups)

        super().change_owner(new_owner)

        to_user = new_owner.user
        to_user.groups.add(*admin_groups)

    @atomic
    def remove_user(self, user):
        auth_groups = Group.objects.filter(
            name__startswith=f"{self.permissions_scope}:"
        )
        user.groups.remove(*list(auth_groups))
        super().remove_user(user)
