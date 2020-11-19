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
        only_fields = (
            "network",
            "billing_seat",
            "budget",
            "title",
            "tags",
            "sending_rules",
            "drips",
            "campaigns",
            "tracking_params",
            "use_credits_method",
            "open_credit_budget",
            "from_name",
        )


class Mutation(graphene.ObjectType):
    mutate_billing_account = BillingAccountMutation.Field()
