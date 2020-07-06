import logging
from collections import OrderedDict
from typing import List

from graphene import relay, GlobalID
from graphene_django import DjangoObjectType
from graphene_django.types import DjangoObjectTypeOptions
from guardian.shortcuts import get_perms
from rest_framework.exceptions import PermissionDenied
from rest_framework.filters import BaseFilterBackend
from rest_framework.permissions import BasePermission

from contrib.rest_framework.permissions import modify_method_for_permissions

logger = logging.getLogger(__name__)


class GuardedObjectTypeOptions(DjangoObjectTypeOptions):
    permission_classes: List[BasePermission] = ()
    filter_backends: List[BaseFilterBackend] = ()

    def get_queryset(self):
        # Small hack to make the ObjectType appear to be a view
        # for the purposes of drf.DjangoModelPermissions
        return self.model.objects.none()


def check_perms(obj, user, required_perms):
    if set(required_perms).issubset(get_perms(user, obj)):
        return obj
    return None


class GuardedObjectType(DjangoObjectType):
    class Meta:
        abstract = True

    @classmethod
    def __init_subclass_with_meta__(
        cls, permission_classes=(), filter_backends=(), _meta=None, **options
    ):

        if not _meta:
            _meta = GuardedObjectTypeOptions(cls)
        _meta.permission_classes = permission_classes
        _meta.filter_backends = filter_backends
        super().__init_subclass_with_meta__(_meta=_meta, **options)

    @classmethod
    def get_permissions(cls):
        """
        Instantiates and returns the list of permissions that this Type requires.
        """
        return [permission() for permission in cls._meta.permission_classes]

    @classmethod
    def check_permissions(cls, context):
        """
        Check if the request should be permitted.
        Raises an appropriate exception if the request is not permitted.
        """
        for permission in cls.get_permissions():
            if not permission.has_permission(context, cls._meta):
                logger.debug(
                    f"{context.user} failed permission check for {cls.__name__} ({permission})"
                )
                raise PermissionDenied(getattr(permission, "message", None))

    @classmethod
    def check_object_permissions(cls, context, obj):
        """
        Check if the request should be permitted for a given object.
        Raises an appropriate exception if the request is not permitted.
        """
        if not obj:
            return obj
        for permission in cls.get_permissions():
            if not permission.has_object_permission(context, cls._meta, obj):
                logger.debug(
                    f"{context.user} failed object permission check for {cls.__name__}"
                )
                raise PermissionDenied(getattr(permission, "message", None))

        return obj

    @classmethod
    def filter_queryset(cls, queryset, context):
        filter_backends = cls._meta.filter_backends
        for backend in list(filter_backends):
            queryset = backend().filter_queryset(context, queryset, cls._meta)
        return queryset

    @classmethod
    def get_queryset(cls, queryset, info):
        with modify_method_for_permissions(info.context, "GET"):
            cls.check_permissions(context=info.context)
            queryset = super().get_queryset(queryset, info)
            queryset = cls.filter_queryset(queryset, context=info.context)
        return queryset

    @classmethod
    def get_node(cls, info, _id):
        with modify_method_for_permissions(info.context, "GET"):
            cls.check_permissions(context=info.context)
            return info.context.loaders.load(cls, _id).then(
                lambda obj: cls.check_object_permissions(context=info.context, obj=obj)
            )

    def resolve_id(self, info):
        try:
            return self.public_id
        except AttributeError:
            return self.pk


class PublicGlobalID(GlobalID):
    def __init__(self, node=None, parent_type=None, required=True, *args, **kwargs):
        super().__init__(
            node=node or ObscureIdNode,
            parent_type=parent_type,
            required=required,
            *args,
            **kwargs,
        )


class ObscureIdNode(relay.Node):
    """An object with an ID"""

    id = GlobalID(
        source="public_id", description="The ID of the object."
    )  # this may not do anything.

    class Meta:
        name = "GraphNode"

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._meta.fields = OrderedDict(
            id=PublicGlobalID(
                cls, source="public_id", description="The ID of the object."
            )  # or maybe this doesn't do anything.
        )
