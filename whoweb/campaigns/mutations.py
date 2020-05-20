import graphene

from whoweb.contrib.graphene_django.mutation import NodeSerializerMutation
from .serializers import SimpleDripCampaignRunnerSerializer


class SimpleCampaignRunnerMutation(NodeSerializerMutation):
    class Meta:
        serializer_class = SimpleDripCampaignRunnerSerializer
        model_operations = (
            "create",
            "update",
            "delete",
        )
        only_fields = (
            "query",
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
    simple_campaign = SimpleCampaignRunnerMutation.Field()
