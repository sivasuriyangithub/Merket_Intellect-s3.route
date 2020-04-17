import logging

from django.db.models import Q
from django.http import Http404
from rest_framework import viewsets
from rest_framework.mixins import RetrieveModelMixin
from rest_framework.viewsets import GenericViewSet

from whoweb.contrib.rest_framework.permissions import IsSuperUser
from ..models import (
    WKPlan,
    WKPlanPreset,
    BillingAccount,
    BillingAccountMember,
)
from ..serializers import (
    PlanSerializer,
    BillingAccountSerializer,
    BillingAccountMemberSerializer,
    PlanPresetSerializer,
)

logger = logging.getLogger(__name__)


class PlanViewSet(viewsets.ModelViewSet):
    lookup_field = "public_id"
    queryset = WKPlan.objects.all()
    serializer_class = PlanSerializer
    permission_classes = [IsSuperUser]


class PlanPresetViewSet(RetrieveModelMixin, GenericViewSet):
    serializer_class = PlanPresetSerializer
    permission_classes = [IsSuperUser]
    queryset = WKPlanPreset.objects.all()

    def get_object(self):
        tag_or_public_id = self.kwargs["pk"]
        if not tag_or_public_id:
            raise Http404
        try:
            plan_preset = WKPlanPreset.objects.get(
                Q(tag=tag_or_public_id) | Q(public_id=tag_or_public_id)
            )
        except WKPlanPreset.DoesNotExist:
            raise Http404
        # May raise a permission denied
        self.check_object_permissions(self.request, plan_preset)
        return plan_preset


class BillingAccountViewSet(viewsets.ModelViewSet):
    lookup_field = "public_id"
    queryset = BillingAccount.objects.all()
    serializer_class = BillingAccountSerializer
    permission_classes = [IsSuperUser]


class BillingAccountMemberViewSet(viewsets.ModelViewSet):
    lookup_field = "public_id"
    queryset = BillingAccountMember.objects.all()
    serializer_class = BillingAccountMemberSerializer
    permission_classes = [IsSuperUser]
