from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from whoweb.payments.exceptions import SubscriptionError, PaymentRequired
from whoweb.contrib.rest_framework.permissions import IsSuperUser
from .models import SimpleDripCampaignRunner, IntervalCampaignRunner
from .serializers import (
    SimpleDripCampaignRunnerSerializer,
    IntervalCampaignRunnerSerializer,
)


class RunnerViewSet(object):
    @action(
        detail=True,
        methods=["post"],
        name="Publish Campaign Runner",
        request_serializer_class=None,
    )
    def publish(self, request, public_id=None):
        runner = self.get_object()
        try:
            runner.publish()
        except SubscriptionError as e:
            raise PaymentRequired(detail=e)
        runner.refresh_from_db()
        return Response(self.get_serializer(runner).data)

    @action(
        detail=True,
        methods=["post"],
        name="Pause Campaign Runner",
        request_serializer_class=None,
    )
    def pause(self, request, public_id=None):
        runner = self.get_object()
        runner.pause()
        runner.refresh_from_db()
        return Response(self.get_serializer(runner).data)

    @action(
        detail=True,
        methods=["post"],
        name="Resume Campaign Runner",
        request_serializer_class=None,
    )
    def resume(self, request, public_id=None):
        runner = self.get_object()
        runner.resume()
        runner.refresh_from_db()
        return Response(self.get_serializer(runner).data)


class SimpleCampaignViewSet(RunnerViewSet, ModelViewSet):
    queryset = SimpleDripCampaignRunner.available_objects.all().order_by("created")
    serializer_class = SimpleDripCampaignRunnerSerializer
    lookup_field = "public_id"
    permission_classes = [IsSuperUser]

    request_serializer_class = SimpleDripCampaignRunnerSerializer
    response_serializer_class = SimpleDripCampaignRunnerSerializer


class IntervalCampaignSerializerViewSet(RunnerViewSet, ModelViewSet):
    queryset = IntervalCampaignRunner.available_objects.all().order_by("created")
    lookup_field = "public_id"
    serializer_class = IntervalCampaignRunnerSerializer
    permission_classes = [IsSuperUser]

    request_serializer_class = IntervalCampaignRunnerSerializer
    response_serializer_class = IntervalCampaignRunnerSerializer
