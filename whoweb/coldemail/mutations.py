import graphene

from whoweb.contrib.graphene_django.mutation import NodeSerializerMutation
from .serializers import (
    CampaignMessageSerializer,
    CampaignMessageTemplateSerializer,
    SingleColdEmailSerializer,
)


class CampaignMessageMutation(NodeSerializerMutation):
    class Meta:
        serializer_class = CampaignMessageSerializer
        model_operations = (
            "create",
            "update",
            "delete",
        )
        only_fields = (
            "billing_seat",
            "title",
            "subject",
            "plain_content",
            "html_content",
            "editor",
            "tags",
        )


class CampaignMessageTemplateMutation(NodeSerializerMutation):
    class Meta:
        serializer_class = CampaignMessageTemplateSerializer
        model_operations = (
            "create",
            "update",
            "delete",
        )
        only_fields = (
            "billing_seat",
            "title",
            "subject",
            "plain_content",
            "html_content",
            "editor",
            "tags",
        )


class SingleRecipientEmailMutation(NodeSerializerMutation):
    class Meta:
        serializer_class = SingleColdEmailSerializer
        model_operations = (
            "create",
            "update",
            "delete",
        )
        only_fields = (
            "message",
            "tags",
            "email",
            "send_date",
            "test",
            "use_credits_method",
            "billing_seat",
            "from_name",
        )


class Mutation(graphene.ObjectType):
    campaign_message = CampaignMessageMutation.Field()
    campaign_message_template = CampaignMessageTemplateMutation.Field()
    single_recipient_email = SingleRecipientEmailMutation.Field()
