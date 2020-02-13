import json
import logging

from django.http import Http404, HttpResponse
from django.views.decorators.http import require_http_methods
from rest_framework.viewsets import ModelViewSet

from whoweb.coldemail.models.reply import ReplyTo
from whoweb.contrib.rest_framework.permissions import IsSuperUser
from .models import (
    CampaignList,
    CampaignMessage,
    CampaignMessageTemplate,
    SingleColdEmail,
)
from .serializers import (
    CampaignListSerializer,
    CampaignMessageSerializer,
    CampaignMessageTemplateSerializer,
    SingleColdEmailSerializer,
)

logger = logging.getLogger(__name__)


@require_http_methods(["POST"])
def replyto_webhook_view(request, match_id):
    try:
        reply_record = ReplyTo.objects.get(match_id)
    except ReplyTo.DoesNotExist:
        raise Http404()

    data = json.loads(request.body)
    logger.info("Reply webhook: {}\nPayload:{}".format(reply_record, data))
    email = data.get("original_source")
    if email:
        reply_record.log_reply(email=email)
    return HttpResponse(status=202)


class CampaignListViewSet(ModelViewSet):
    serializer_class = CampaignListSerializer
    queryset = CampaignList.objects.all()
    lookup_field = "public_id"
    permission_classes = [IsSuperUser]


class CampaignMessageViewSet(ModelViewSet):
    serializer_class = CampaignMessageSerializer
    queryset = CampaignMessage.objects.all()
    lookup_field = "public_id"
    permission_classes = [IsSuperUser]


class CampaignMessageTemplateViewSet(ModelViewSet):
    serializer_class = CampaignMessageTemplateSerializer
    queryset = CampaignMessageTemplate.objects.all()
    lookup_field = "public_id"
    permission_classes = [IsSuperUser]


class SingleEmailViewSet(ModelViewSet):
    serializer_class = SingleColdEmailSerializer
    queryset = SingleColdEmail.objects.all()
    lookup_field = "public_id"
    permission_classes = [IsSuperUser]
