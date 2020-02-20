# Create your views here.
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from whoweb.coldemail.serializers import CampaignSerializer
from whoweb.contrib.rest_framework.permissions import IsSuperUser
from .models import SimpleDripCampaignRunner, IntervalCampaignRunner
from .serializers import (
    SimpleDripCampaignRunnerSerializer,
    IntervalCampaignRunnerSerializer,
)


class RunnerViewSet(object):
    @action(detail=True, methods=["post"])
    def publish(self, request, public_id=None):
        runner = self.get_object()
        runner.publish()
        runner.refresh_from_db()
        return Response(self.get_serializer(runner).data)

    @action(detail=True, methods=["post"])
    def pause(self, request, public_id=None):
        runner = self.get_object()
        runner.pause()
        runner.refresh_from_db()
        return Response(self.get_serializer(runner).data)

    @action(detail=True, methods=["post"])
    def resume(self, request, public_id=None):
        runner = self.get_object()
        runner.resume()
        runner.refresh_from_db()
        return Response(self.get_serializer(runner).data)


class SimpleCampaignViewSet(RunnerViewSet, ModelViewSet):
    queryset = SimpleDripCampaignRunner.objects.all()
    serializer_class = SimpleDripCampaignRunnerSerializer
    lookup_field = "public_id"
    permission_classes = [IsSuperUser]


class IntervalCampaignSerializerViewSet(RunnerViewSet, ModelViewSet):
    queryset = IntervalCampaignRunner.objects.all()
    lookup_field = "public_id"
    serializer_class = IntervalCampaignRunnerSerializer
    permission_classes = [IsSuperUser]
