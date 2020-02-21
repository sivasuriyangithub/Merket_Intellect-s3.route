from rest_framework import routers

from .views import PlanViewSet, AdminBillingSeatViewSet

app_name = "payments"

router = routers.SimpleRouter()
router.register(r"plans", PlanViewSet)
router.register(r"admin/seats", AdminBillingSeatViewSet, basename="seatadmin")

urlpatterns = []
