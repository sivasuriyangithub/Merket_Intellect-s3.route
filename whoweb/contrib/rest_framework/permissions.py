from contextlib import contextmanager
from typing import Type

from rest_framework import permissions
import logging

logger = logging.getLogger(__name__)


class IsSuperUser(permissions.BasePermission):
    """
    Allows access only to superusers.
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_superuser)

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


def ObjectPassesTest(func: callable) -> Type[permissions.BasePermission]:
    class Passes(permissions.BasePermission):
        # def has_permission(self, request, view):
        #     return False

        def has_object_permission(self, request, view, obj):
            return func(request.user, obj)

    return Passes


class ObjectPermissions(permissions.DjangoObjectPermissions):
    """
    Similar to `DjangoObjectPermissions`, but adding 'view' permissions.
    """

    perms_map = {
        "GET": ["%(app_label)s.view_%(model_name)s"],
        "OPTIONS": ["%(app_label)s.view_%(model_name)s"],
        "HEAD": ["%(app_label)s.view_%(model_name)s"],
        "POST": [
            "%(app_label)s.view_%(model_name)s",
            "%(app_label)s.add_%(model_name)s",
        ],
        "PUT": [
            "%(app_label)s.view_%(model_name)s",
            "%(app_label)s.change_%(model_name)s",
        ],
        "PATCH": [
            "%(app_label)s.view_%(model_name)s",
            "%(app_label)s.change_%(model_name)s",
        ],
        "DELETE": [
            "%(app_label)s.view_%(model_name)s",
            "%(app_label)s.delete_%(model_name)s",
        ],
    }

    def get_required_object_permissions(self, method, model_cls):
        perms = super().get_required_object_permissions(method, model_cls)
        logger.debug(perms)
        return perms


@contextmanager
def modify_method_for_permissions(context, operation):
    """
    While DRF understands request methods, GraphQL is always POST.
    To encourage reuse of ObjectPermissions, mutations should wrap permission checks
    with the relevant method.
    """
    try:
        if not hasattr(context, "_original_method"):
            context._original_method = context.method
        context.method = operation
        yield context
    finally:
        if hasattr(context, "_original_method"):
            context.method = context._original_method
            del context._original_method
