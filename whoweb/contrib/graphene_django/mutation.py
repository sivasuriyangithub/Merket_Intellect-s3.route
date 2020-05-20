from collections import OrderedDict

import graphene
from django.db.models import Model
from django.http import Http404
from django.shortcuts import get_object_or_404
from graphene.relay.mutation import ClientIDMutation
from graphene.types import Field, InputField
from graphene.types.mutation import MutationOptions
from graphene.types.objecttype import yank_fields_from_attrs
from graphene_django.registry import get_global_registry, Registry
from graphene_django.rest_framework.serializer_converter import convert_serializer_field
from graphene_django.types import ErrorType
from rest_framework.serializers import Serializer

from whoweb.contrib.rest_framework.permissions import modify_method_for_permissions


class SerializerMutationOptions(MutationOptions):
    lookup_field = None
    model_class: Model = None
    model_operations = ["create", "update", "delete"]
    serializer_class: Serializer = None
    object_type: graphene.ObjectType = None
    registry: Registry = None


def fields_for_serializer(
    serializer,
    only_fields,
    exclude_fields,
    is_input=False,
    convert_choices_to_enum=True,
):
    fields = OrderedDict()
    for name, field in serializer.fields.items():
        is_not_in_only = only_fields and name not in only_fields
        is_excluded = any(
            [
                name in exclude_fields,
                field.write_only
                and not is_input,  # don't show write_only fields in Query
                field.read_only and is_input,  # don't show read_only fields in Input
            ]
        )

        if is_not_in_only or is_excluded:
            continue

        fields[name] = convert_serializer_field(
            field, is_input=is_input, convert_choices_to_enum=convert_choices_to_enum
        )
    return fields


class NodeSerializerMutation(ClientIDMutation):
    class Meta:
        abstract = True

    errors = graphene.List(
        ErrorType, description="May contain more than one error for same field."
    )

    @classmethod
    def __init_subclass_with_meta__(
        cls,
        lookup_field=None,
        serializer_class=None,
        model_class=None,
        model_operations=("create", "update", "delete"),
        only_fields=(),
        exclude_fields=(),
        convert_choices_to_enum=True,
        object_type=None,
        registry=None,
        **options
    ):

        if not serializer_class:
            raise Exception("serializer_class is required for the SerializerMutation")

        if "update" not in model_operations and "create" not in model_operations:
            raise Exception('model_operations must contain "create" and/or "update"')

        serializer = serializer_class()
        if model_class is None:
            serializer_meta = getattr(serializer_class, "Meta", None)
            if serializer_meta:
                model_class = getattr(serializer_meta, "model", None)
        if object_type is None:
            if model_class is None:
                raise Exception(
                    "object_type is required SerializerMutation if no model is specified."
                )
            if not registry:
                registry = get_global_registry()
            object_type = registry.get_type_for_model(model_class)

        if lookup_field is None and model_class:
            lookup_field = model_class._meta.pk.name

        input_fields = fields_for_serializer(
            serializer,
            only_fields,
            exclude_fields,
            is_input=True,
            convert_choices_to_enum=convert_choices_to_enum,
        )

        output_fields = OrderedDict()
        output_fields["node"] = graphene.Field(object_type)

        _meta = SerializerMutationOptions(cls)
        _meta.lookup_field = lookup_field
        _meta.model_operations = model_operations
        _meta.serializer_class = serializer_class
        _meta.model_class = model_class
        _meta.object_type = object_type
        _meta.registry = registry
        _meta.fields = yank_fields_from_attrs(output_fields, _as=Field)

        input_fields = yank_fields_from_attrs(input_fields, _as=InputField)

        if "delete" in model_operations:
            input_fields["deleted"] = graphene.Boolean(default=False)
        super(NodeSerializerMutation, cls).__init_subclass_with_meta__(
            _meta=_meta, input_fields=input_fields, **options
        )

    @classmethod
    def get_serializer_kwargs(cls, root, info, **input):
        lookup_field = cls._meta.lookup_field
        object_type = cls._meta.object_type
        if "update" in cls._meta.model_operations and lookup_field in input:
            info.context.method = "PATCH"
            with modify_method_for_permissions(info.context, "PATCH"):
                instance = object_type.get_node(info, input[lookup_field])
            if not instance:
                raise Http404(
                    "No %s matches the given query."
                    % object_type._meta.model._meta.object_name
                )
            partial = True
        elif "create" in cls._meta.model_operations:
            object_type.check_permissions(context=info.context)
            instance = None
            partial = False
        else:
            raise Exception(
                'Invalid update operation. Input parameter "{}" required.'.format(
                    lookup_field
                )
            )
        return {
            "instance": instance,
            "data": input,
            "context": {"request": info.context},
            "partial": partial,
        }

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        lookup_field = cls._meta.lookup_field
        object_type = cls._meta.object_type
        delete = input.pop("deleted", False)
        if "delete" in cls._meta.model_operations and lookup_field in input and delete:
            with modify_method_for_permissions(info.context, "DELETE"):
                instance = object_type.get_node(info, input[lookup_field])
            if not instance:
                raise Http404(
                    "No %s matches the given query."
                    % object_type._meta.model._meta.object_name
                )
            instance.delete()
            return cls(errors=None, node=None)
        kwargs = cls.get_serializer_kwargs(root, info, **input)
        serializer = cls._meta.serializer_class(**kwargs)

        if serializer.is_valid():
            return cls.perform_mutate(serializer, info)
        else:
            errors = ErrorType.from_errors(serializer.errors)
            return cls(errors=errors)

    @classmethod
    def perform_mutate(cls, serializer, info):
        obj = serializer.save()
        return cls(errors=None, node=obj)
