from rest_framework import routers

from whoweb.users.views import SeatViewSet, DeveloperKeyViewSet, NetworkViewSet

app_name = "users"

router = routers.SimpleRouter()
router.register(r"seats", SeatViewSet)
router.register(r"networks", NetworkViewSet)
router.register(r"developer_keys", DeveloperKeyViewSet)

urlpatterns = []
