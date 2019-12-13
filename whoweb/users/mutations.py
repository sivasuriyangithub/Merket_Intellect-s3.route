import graphene
from django import http
from graphene_django.rest_framework.mutation import SerializerMutation
from graphql_jwt import ObtainJSONWebToken

from whoweb.users.models import Seat, OrganizationCredentials
from whoweb.users.serializers import OrganizationCredentialsSerializer


class DeveloperKeyMutation(SerializerMutation):
    class Meta:
        serializer_class = OrganizationCredentialsSerializer

    @classmethod
    def get_serializer_kwargs(cls, root, info, **input):
        if "id" in input:
            instance = OrganizationCredentials.objects.filter(id=input["id"]).first()
            if instance:
                return {"instance": instance, "data": input, "partial": True}

            else:
                raise http.Http404

        return {"data": input, "partial": True}


class Mutation(graphene.ObjectType):
    # seat = SeatMutation.Field()
    pass
