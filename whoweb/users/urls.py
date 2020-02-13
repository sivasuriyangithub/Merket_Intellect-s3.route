from rest_framework import routers

from whoweb.users.views import (
    SeatViewSet,
    DeveloperKeyViewSet,
    NetworkViewSet,
    UserViewSet,
    AdminBillingSeatViewSet,
)

app_name = "users"

router = routers.SimpleRouter()
router.register(r"users", UserViewSet)
router.register(r"seats", SeatViewSet)
router.register(r"admin/seats", AdminBillingSeatViewSet, basename="seatadmin")
router.register(r"networks", NetworkViewSet)
router.register(r"developer_keys", DeveloperKeyViewSet)

urlpatterns = []
