import graphene
from django import http

from whoweb.contrib.graphene_django.mutation import NodeSerializerMutation
from whoweb.users.models import DeveloperKey
from whoweb.users.serializers import DeveloperKeySerializer


class DeveloperKeyMutation(NodeSerializerMutation):
    class Meta:
        serializer_class = DeveloperKeySerializer

    @classmethod
    def get_serializer_kwargs(cls, root, info, **input):
        if "id" in input:
            instance = DeveloperKey.objects.filter(id=input["id"]).first()
            if instance:
                return {"instance": instance, "data": input, "partial": True}
            else:
                raise http.Http404

        return {"data": input, "partial": True}


class Mutation(graphene.ObjectType):
    mutate_developer_key = DeveloperKeyMutation.Field()
