from functools import partial
from typing import List, Optional

from django.contrib.contenttypes.models import ContentType
from graphene_django import DjangoObjectType
from graphene_django.types import DjangoObjectTypeOptions
from graphql_jwt.decorators import permission_required
from guardian.shortcuts import get_objects_for_user, get_perms


class ProtectedDjangoObjectTypeOptions(DjangoObjectTypeOptions):
    permissions: Optional[List[str]] = None
    object_permissions: Optional[List[str]] = None


def check_perms(obj, user, required_perms):
    if set(required_perms).issubset(get_perms(user, obj)):
        return obj
    return None


class ProtectedDjangoObjectType(DjangoObjectType):
    class Meta:
        abstract = True

    @classmethod
    def __init_subclass_with_meta__(cls, **options):
        options.setdefault("_meta", ProtectedDjangoObjectTypeOptions(cls))
        super().__init_subclass_with_meta__(**options)

    @classmethod
    def get_model_permissions(cls):
        if cls._meta.permissions:
            return cls._meta.permissions
        ct = ContentType.objects.get_for_model(cls._meta.model)
        return (f"{ct.app_label}.view_{ct.model}",)

    @classmethod
    def get_object_permissions(cls):
        if cls._meta.object_permissions:
            return cls._meta.object_permissions
        return cls.get_model_permissions()

    @classmethod
    def get_node(cls, info, _id):
        if all(
            permission_required(perm)(info.context.user)
            for perm in cls.get_model_permissions()
        ):
            return info.context.loaders.load(cls, _id).then(
                partial(
                    check_perms,
                    user=info.context.user,
                    required_perms=cls.get_object_permissions(),
                )
            )

    @classmethod
    def get_queryset(cls, queryset, info):
        if all(permission_required(perm) for perm in cls.get_model_permissions()):
            return get_objects_for_user(
                info.context.user,
                cls.get_object_permissions(),
                klass=super().get_queryset(queryset, info),
                accept_global_perms=False,
            )
