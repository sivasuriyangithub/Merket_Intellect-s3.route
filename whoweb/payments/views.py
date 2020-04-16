import logging
from datetime import datetime, timedelta
from typing import Union

from IPython.utils.tz import utcnow
from django.db.models import Q
from django.http import Http404
from djstripe.enums import SubscriptionStatus
from djstripe.models import Customer, Subscription
from djstripe.settings import CANCELLATION_AT_PERIOD_END
from rest_framework import viewsets, status
from rest_framework.exceptions import ValidationError, MethodNotAllowed
from rest_framework.mixins import RetrieveModelMixin
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from whoweb.core.utils import IdempotentRequest
from whoweb.contrib.rest_framework.permissions import IsSuperUser
from whoweb.users.models import Seat
from .models import (
    WKPlan,
    WKPlanPreset,
    BillingAccount,
    BillingAccountMember,
)
from .serializers import (
    PlanSerializer,
    AdminBillingSeatSerializer,
    CreateSubscriptionSerializer,
    UpdateSubscriptionSerializer,
    BillingAccountSerializer,
    AddPaymentSourceSerializer,
    AdminBillingAccountSerializer,
    BillingAccountMemberSerializer,
    SubscriptionSerializer,
    PlanPresetSerializer,
    CreditChargeSerializer,
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


class AdminBillingSeatViewSet(viewsets.ModelViewSet):
    lookup_field = "public_id"
    queryset = Seat.objects.all()
    serializer_class = AdminBillingSeatSerializer
    permission_classes = [IsSuperUser]


class AdminBillingAccountViewSet(viewsets.ModelViewSet):
    lookup_field = "public_id"
    queryset = Seat.objects.all()
    serializer_class = AdminBillingAccountSerializer
    permission_classes = [IsSuperUser]


class AddPaymentSourceRestView(APIView):
    # TODO: user passes test Can Edit Customer
    def post(self, request, **kwargs):
        serializer = AddPaymentSourceSerializer(
            data=request.data, context={"request": request}
        )

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        billing_account: BillingAccount = serializer.validated_data["billing_account"]
        customer, _created = Customer.get_or_create(subscriber=billing_account)
        customer.add_card(serializer.validated_data["stripe_token"])

        if subscription := customer.subscription:
            if (
                subscription.status == SubscriptionStatus.trialing
                and subscription.trial_end > datetime.utcnow()
            ):
                subscription.update(trial_end="now")
            elif subscription.status == SubscriptionStatus.unpaid:
                for invoice in customer.invoices:
                    if (
                        datetime.utcfromtimestamp(invoice.period_end)
                        < datetime.utcnow()
                        and invoice.amount_remaining > 0
                        and not invoice.forgiven
                    ):
                        stripe_invoice = invoice.api_retrieve()
                        updated_stripe_invoice = stripe_invoice.pay(forgive=True)
                        type(stripe_invoice).sync_from_stripe_data(
                            updated_stripe_invoice
                        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class SubscriptionRestView(APIView):
    def post(self, request, **kwargs):
        serializer = CreateSubscriptionSerializer(
            data=request.data, context={"request": request}
        )

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        valid_items, plan_preset, total_credits = self._get_valid_items(serializer)
        wkplan = plan_preset.create()
        billing_account: BillingAccount = serializer.validated_data["billing_account"]
        billing_account.update_plan(
            initiated_by=self.request.user, new_plan=wkplan, with_credits=total_credits,
        )

        customer, _created = Customer.get_or_create(subscriber=billing_account)
        if customer.valid_subscriptions:
            raise MethodNotAllowed(
                method="POST", detail="Customer already subscribed, use PATCH instead."
            )
        token = serializer.validated_data.get("stripe_token")
        trial_days = serializer.validated_data.get("trial_days", None)

        if trial_days is None:
            trial_days = plan_preset.trial_days_allowed
        if trial_days == 0:
            trial_end = "now"
        elif trial_days > plan_preset.trial_days_allowed:
            raise ValidationError(
                f"Invalid number of trial days. Must be less than {plan_preset.trial_days_allowed}."
            )
        else:
            trial_end = str(round((utcnow() + timedelta(days=trial_days)).timestamp()))

        if token:
            customer.add_card(token)

        stripe_subscription = Subscription._api_create(
            items=valid_items, customer=customer.id, trial_end=trial_end,
        )
        Subscription.sync_from_stripe_data(stripe_subscription)

        charge_immediately = serializer.validated_data.get("charge_immediately")
        if charge_immediately is None or not token:
            charge_immediately = False
        if charge_immediately:
            customer.send_invoice()

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def patch(self, request, **kwargs):
        serializer = UpdateSubscriptionSerializer(
            data=request.data, context={"request": request}
        )

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        billing_account: BillingAccount = serializer.validated_data["billing_account"]
        customer, _created = Customer.get_or_create(subscriber=billing_account)
        token = serializer.validated_data.get("stripe_token")
        if token:
            customer.add_card(token)

        valid_items, preset, total_credits = self._get_valid_items(serializer)

        subscription = customer.subscription
        patch_items_by_id = {item["plan"]: item for item in valid_items}
        current_items_by_id = {item.plan.id: item for item in subscription.items.all()}

        settable_items = []
        items_for_manual_deletion = []
        for plan_id, patch_item in patch_items_by_id.items():
            if plan_id in current_items_by_id:
                patch_item["id"] = current_items_by_id[plan_id].id
            settable_items.append(patch_item)
        for plan_id, existing_item in current_items_by_id.items():
            if plan_id not in patch_items_by_id:
                settable_items.append(
                    {"plan": plan_id, "id": existing_item.id, "deleted": True}
                )
                items_for_manual_deletion.append(existing_item)

        stripe_subscription = subscription.api_retrieve()
        setattr(stripe_subscription, "items", settable_items)
        Subscription.sync_from_stripe_data(stripe_subscription.save())
        for item in items_for_manual_deletion:
            item.delete()

        charge_immediately = serializer.validated_data.get("charge_immediately")
        if charge_immediately is None or not token:
            charge_immediately = False
        if charge_immediately:
            customer.send_invoice()

        return Response(serializer.data, status=status.HTTP_200_OK)

    def _get_valid_items(
        self,
        serializer: Union[CreateSubscriptionSerializer, UpdateSubscriptionSerializer],
    ) -> (dict, WKPlan, int):
        tag_or_public_id = serializer.validated_data.get("plan")
        plan_preset = WKPlanPreset.objects.filter(
            Q(tag=tag_or_public_id) | Q(public_id=tag_or_public_id)
        ).first()
        if not plan_preset:
            raise ValidationError("A valid plan id or tag must be specified.")
        valid_monthly_plans = plan_preset.stripe_plans_monthly.in_bulk(field_name="id")
        valid_yearly_plans = plan_preset.stripe_plans_yearly.in_bulk(field_name="id")

        valid_items = []
        total_credits = 0
        at_least_one_non_addon_product = False
        for item in serializer.validated_data["items"]:
            plan_id, quantity = item["stripe_id"], item["quantity"]
            if plan_id in valid_monthly_plans:
                plan = valid_monthly_plans[plan_id]
            elif plan_id in valid_yearly_plans:
                plan = valid_yearly_plans[plan_id]
            else:
                raise ValidationError("Invalid items.")
            if plan.product.metadata.get("product") == "credits":
                total_credits += quantity
            if plan.product.metadata.get("is_addon") == "false":
                at_least_one_non_addon_product = True
            valid_items.append({"plan": plan_id, "quantity": quantity})
        if not at_least_one_non_addon_product:
            raise ValidationError("Invalid items.")
        return valid_items, plan_preset, total_credits

    def get(self, request, billing_account_id, **kwargs):
        """
        Return the customer's valid subscriptions.

        Returns with status code 200.
        """
        try:
            billing_account = BillingAccount.objects.get(pk=billing_account_id)
        except ValueError:
            billing_account = BillingAccount.objects.get(public_id=billing_account_id)
        customer, _created = Customer.get_or_create(subscriber=billing_account)
        serializer = SubscriptionSerializer(customer.subscription)
        return Response(serializer.data)

    def delete(self, request, billing_account_id, **kwargs):
        """
        Mark the customers current subscription as canceled.

        Returns with status code 204.
        """
        try:
            billing_account = BillingAccount.objects.get(pk=billing_account_id)
        except ValueError:
            billing_account = BillingAccount.objects.get(public_id=billing_account_id)

        customer, _created = Customer.get_or_create(subscriber=billing_account)
        customer.subscription.cancel(at_period_end=CANCELLATION_AT_PERIOD_END)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CreditChargeRestView(APIView):
    def post(self, request, **kwargs):
        serializer = CreditChargeSerializer(
            data=request.data, context={"request": request}
        )

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        billing_account: BillingAccount = serializer.validated_data.pop(
            "billing_account"
        )

        idempotency = IdempotentRequest(request)
        if idempotency.is_idempotent():
            try:
                success = billing_account.consume_credits(**serializer.validated_data)
            except:
                idempotency.rewind()
                raise
        else:
            success = True
        if success:
            return Response(serializer.data, status=status.HTTP_202_ACCEPTED)
        else:
            return Response(serializer.data, status=status.HTTP_402_PAYMENT_REQUIRED)
