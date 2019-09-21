from django.urls import path
from rest_framework import routers

from whoweb.users.views import SeatViewSet

app_name = "users"

router = routers.SimpleRouter()
router.register(r"seats", SeatViewSet)

urlpatterns = []
