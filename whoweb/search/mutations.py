import graphene
from graphene_django.rest_framework.mutation import SerializerMutation
from graphql_jwt.decorators import login_required

from whoweb.contrib.graphene_django.mutation import NodeSerializerMutation
from .schema import ResultProfileObjectType
from .serializers import DeriveContactSerializer, FilterValueListSerializer


class DeriveContact(SerializerMutation):
    profile = graphene.Field(ResultProfileObjectType)

    class Meta:
        serializer_class = DeriveContactSerializer
        model_operations = ("create",)
        exclude_fields = ("initiated_by",)

    @classmethod
    @login_required
    def get_serializer_kwargs(cls, root, info, **input):
        return {
            "data": input,
            "context": {"request": info.context},
            "partial": False,
        }


class FilterValueListMutation(NodeSerializerMutation):
    class Meta:
        serializer_class = FilterValueListSerializer
        model_operations = (
            "create",
            "update",
            "delete",
        )


class Mutation(graphene.ObjectType):
    derive_contact = DeriveContact.Field()
    filter_value_list = FilterValueListMutation.Field()
