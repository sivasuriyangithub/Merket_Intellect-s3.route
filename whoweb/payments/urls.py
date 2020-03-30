from rest_framework import routers

from .views import (
    PlanViewSet,
    AdminBillingSeatViewSet,
    BillingAccountViewSet,
    AdminBillingAccountViewSet,
    BillingAccountMemberViewSet,
    PlanPresetViewSet,
)

app_name = "payments"

router = routers.SimpleRouter()
router.register(r"plans", PlanViewSet)
router.register(r"plan_presets", PlanPresetViewSet)
router.register(r"billing_accounts", BillingAccountViewSet)
router.register(r"account_members", BillingAccountMemberViewSet)
router.register(r"admin/seats", AdminBillingSeatViewSet, basename="seatadmin")
router.register(
    r"admin/billing_accounts", AdminBillingAccountViewSet, basename="accountadmin"
)

urlpatterns = []
