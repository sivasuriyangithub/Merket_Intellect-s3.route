import logging

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as CoreValidationError
from django.db.models import Q
from django.http import Http404
from django_filters.rest_framework import DjangoFilterBackend
from djstripe.exceptions import MultipleSubscriptionException
from djstripe.settings import CANCELLATION_AT_PERIOD_END
from rest_framework import status, mixins
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from whoweb.contrib.rest_framework.filters import ObjectPermissionsFilter
from whoweb.contrib.rest_framework.permissions import IsSuperUser, ObjectPermissions
from ..exceptions import PaymentRequired
from ..models import (
    WKPlan,
    WKPlanPreset,
    BillingAccount,
    BillingAccountMember,
)
from ..permissions import BillingAccountMemberPermissionsFilter
from ..serializers import (
    PlanSerializer,
    BillingAccountSerializer,
    BillingAccountMemberSerializer,
    PlanPresetSerializer,
    BillingAccountSubscriptionSerializer,
    ManageMemberCreditsSerializer,
)

logger = logging.getLogger(__name__)

User = get_user_model()


class PlanViewSet(mixins.RetrieveModelMixin, mixins.ListModelMixin, GenericViewSet):
    lookup_field = "public_id"
    queryset = WKPlan.available_objects.all()
    serializer_class = PlanSerializer
    permission_classes = [IsSuperUser]


class PlanPresetViewSet(
    mixins.RetrieveModelMixin, mixins.ListModelMixin, GenericViewSet
):
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


class BillingAccountViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    lookup_field = "public_id"
    queryset = BillingAccount.objects.all()
    serializer_class = BillingAccountSerializer
    permission_classes = [IsSuperUser | ObjectPermissions]
    filter_backends = [DjangoFilterBackend, ObjectPermissionsFilter]

    request_serializer_class = BillingAccountSerializer
    response_serializer_class = BillingAccountSerializer

    @action(
        detail=True,
        methods=["post", "patch"],
        name="Subscription",
        request_serializer_class=BillingAccountSubscriptionSerializer,
        permission_classes=[IsAuthenticated],
        filter_backends=[DjangoFilterBackend, ObjectPermissionsFilter],
        url_path="subscription",
    )
    def subscription(self, request, public_id=None):
        billing_account: BillingAccount = self.get_object()

        if not request.user.has_perm("change_billingaccount", billing_account):
            self.permission_denied(request)

        serializer = BillingAccountSubscriptionSerializer(
            data=request.data, context={"request": request}
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        is_post = self.request.method == "POST"
        try:
            if is_post:
                billing_account.subscribe(**serializer.validated_data)
            else:
                billing_account.update_subscription(**serializer.validated_data)
        except MultipleSubscriptionException:
            raise MethodNotAllowed(
                method="POST", detail="Customer already subscribed, use PATCH instead."
            )
        except CoreValidationError as e:
            raise ValidationError(e)
        billing_account.refresh_from_db()
        billing_account.set_pool_for_all_members()  # TODO: remove and make clients manage
        return Response(
            BillingAccountSerializer(
                billing_account, context={"request": request}
            ).data,
            status=status.HTTP_201_CREATED if is_post else status.HTTP_200_OK,
        )

    @subscription.mapping.delete
    def cancel_subscription(self, request, public_id=None):
        billing_account: BillingAccount = self.get_object()
        if not request.user.has_perm("change_billingaccount", billing_account):
            self.permission_denied(request)
        billing_account.subscription.cancel(at_period_end=CANCELLATION_AT_PERIOD_END)
        return Response(
            BillingAccountSerializer(billing_account, context={"request": request}).data
        )

    @action(
        detail=True,
        methods=["post"],
        name="Set Member Credits",
        request_serializer_class=ManageMemberCreditsSerializer,
    )
    def credits(self, request, public_id=None):
        """

        :param request:
        :type request:
        :param pk:
        :type pk:
        :return:
        :rtype:
        """
        billing_account = self.get_object()
        serializer = ManageMemberCreditsSerializer(
            data=request.data, context={"request": request}
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        member: BillingAccountMember = serializer.validated_data["billing_seat"]
        if serializer.validated_data["pool"] is True:
            member.pool_credits = True
            member.save()
            target = 0
        else:
            target = serializer.validated_data["credits"]
        updated = billing_account.set_member_credits(member=member, target=target)
        if not updated:
            raise PaymentRequired

        member.refresh_from_db()
        return Response(
            BillingAccountMemberSerializer(member, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )


class BillingAccountMemberViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    lookup_field = "public_id"
    queryset = BillingAccountMember.objects.all()
    serializer_class = BillingAccountMemberSerializer
    permission_classes = [IsSuperUser | ObjectPermissions]
    filter_backends = [
        ObjectPermissionsFilter,
        BillingAccountMemberPermissionsFilter,
    ]

    def check_permissions(self, request):
        try:
            request.user = User.objects.get(pk=request.user.pk)
        except User.DoesNotExist:
            pass
        # if self.request.method == "POST":
        #     serializer = self.get_serializer()
        #     billing_account = serializer.data["billing_account"]
        #     if not request.user.has_perm("add_billingaccountmembers", billing_account):
        #         return self.permission_denied(request)
        return super(BillingAccountMemberViewSet, self).check_permissions(request)
