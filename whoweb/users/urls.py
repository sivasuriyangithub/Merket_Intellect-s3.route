from django.urls import path
from rest_framework import routers

from whoweb.users.views import SeatViewSet, OrganizationCredentialsSerializerViewSet

app_name = "users"

router = routers.SimpleRouter()
router.register(r"seats", SeatViewSet)
router.register(r"developer_keys", OrganizationCredentialsSerializerViewSet)

urlpatterns = []
