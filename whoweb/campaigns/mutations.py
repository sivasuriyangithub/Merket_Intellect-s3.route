import graphene

from whoweb.contrib.graphene_django.mutation import NodeSerializerMutation
from .serializers import (
    SimpleDripCampaignRunnerSerializer,
    IntervalCampaignRunnerSerializer,
)


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
            "saved_search",
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


class IntervalCampaignRunnerMutation(NodeSerializerMutation):
    class Meta:
        serializer_class = IntervalCampaignRunnerSerializer
        model_operations = (
            "create",
            "update",
            "delete",
        )
        only_fields = (
            "query",
            "saved_search",
            "billing_seat",
            "budget",
            "title",
            "tags",
            "sending_rules",
            "drips",
            "campaigns",
            "tracking_params",
            "interval_hours",
            "max_sends",
            "from_name",
        )


class Mutation(graphene.ObjectType):
    simple_campaign = SimpleCampaignRunnerMutation.Field()
    interval_campaign = IntervalCampaignRunnerMutation.Field()
