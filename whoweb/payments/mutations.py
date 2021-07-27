import graphene

from .serializers import BillingAccountSerializer
from whoweb.contrib.graphene_django.mutation import NodeSerializerMutation


class BillingAccountMutation(NodeSerializerMutation):
    class Meta:
        serializer_class = BillingAccountSerializer
        model_operations = (
            "create",
            "delete",
        )
        only_fields = ("customer_type",)


class Mutation(graphene.ObjectType):
    mutate_billing_account = BillingAccountMutation.Field()
