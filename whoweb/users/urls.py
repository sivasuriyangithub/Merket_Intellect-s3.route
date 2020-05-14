from django.urls import path
from rest_framework import routers

from whoweb.users.views import (
    SeatViewSet,
    DeveloperKeyViewSet,
    NetworkViewSet,
    UserViewSet,
    ManageUserAuthenticationAPIView,
)

app_name = "users"

router = routers.SimpleRouter()
router.register(r"users", UserViewSet)
router.register(r"seats", SeatViewSet)
router.register(r"networks", NetworkViewSet)
router.register(r"developer_keys", DeveloperKeyViewSet)


urlpatterns = [
    path("set_password/", ManageUserAuthenticationAPIView.as_view()),
]
