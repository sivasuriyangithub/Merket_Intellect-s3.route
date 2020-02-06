import json
import logging

from django.http import Http404, HttpResponse

# Create your views here.
from django.views.decorators.http import require_http_methods
from rest_framework.permissions import IsAdminUser
from rest_framework.viewsets import ModelViewSet

from .models import CampaignList, CampaignMessage, ColdCampaign
from .serializers import (
    CampaignSerializer,
    CampaignListSerializer,
    CampaignMessageSerializer,
)
from whoweb.contrib.rest_framework.permissions import IsSuperUser
from whoweb.coldemail.models.reply import ReplyTo

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

    def get_permissions(self):
        if self.action == "create":
            return [IsSuperUser()]
        else:
            return [IsAdminUser()]


class CampaignMessageViewSet(ModelViewSet):
    serializer_class = CampaignMessageSerializer
    queryset = CampaignMessage.objects.all()
    lookup_field = "public_id"

    def get_permissions(self):
        if self.action == "create":
            return [IsSuperUser()]
        else:
            return [IsAdminUser()]


class CampaignViewSet(ModelViewSet):
    serializer_class = CampaignSerializer
    queryset = ColdCampaign.objects.all()
    lookup_field = "public_id"

    def get_permissions(self):
        if self.action == "create":
            return [IsSuperUser()]
        else:
            return [IsAdminUser()]
