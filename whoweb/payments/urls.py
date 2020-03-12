from rest_framework import routers

from .views import PlanViewSet, AdminBillingSeatViewSet, BillingAccountViewSet

app_name = "payments"

router = routers.SimpleRouter()
router.register(r"plans", PlanViewSet)
router.register(r"billing_accounts", BillingAccountViewSet)
router.register(r"admin/seats", AdminBillingSeatViewSet, basename="seatadmin")

urlpatterns = []
