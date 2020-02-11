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


class SimpleCampaignViewSet(ModelViewSet):
    queryset = SimpleDripCampaignRunner.objects.all()
    serializer_class = SimpleDripCampaignRunnerSerializer
    lookup_field = "public_id"

    def get_permissions(self):
        if self.action == "create":
            return [IsSuperUser()]
        else:
            return [IsAdminUser()]


class IntervalCampaignSerializerViewSet(ModelViewSet):
    queryset = IntervalCampaignRunner.objects.all()
    lookup_field = "public_id"
    serializer_class = IntervalCampaignRunnerSerializer

    def get_permissions(self):
        if self.action == "create":
            return [IsSuperUser()]
        else:
            return [IsAdminUser()]
