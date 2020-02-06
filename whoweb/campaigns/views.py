from django.shortcuts import render

# Create your views here.
from rest_framework.permissions import IsAdminUser
from rest_framework.viewsets import ModelViewSet

from .models import SimpleDripCampaignRunner, IntervalCampaignRunner
from .serializers import (
    SimpleDripCampaignRunnerSerializer,
    IntervalCampaignRunnerSerializer,
)
from whoweb.contrib.rest_framework.permissions import IsSuperUser


class SimpleCampaignRunnerViewSet(ModelViewSet):
    queryset = SimpleDripCampaignRunner.objects.all()
    serializer_class = SimpleDripCampaignRunnerSerializer

    def get_permissions(self):
        if self.action == "create":
            return [IsSuperUser()]
        else:
            return [IsAdminUser()]


class IntervalCampaignRunnerSerializerViewSet(ModelViewSet):
    queryset = IntervalCampaignRunner.objects.all()

    serializer_class = IntervalCampaignRunnerSerializer

    def get_permissions(self):
        if self.action == "create":
            return [IsSuperUser()]
        else:
            return [IsAdminUser()]
