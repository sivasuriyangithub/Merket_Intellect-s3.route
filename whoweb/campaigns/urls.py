from django.urls import path
from rest_framework.routers import SimpleRouter
from . import views
from whoweb.coldemail.views import replyto_webhook_view

app_name = "campaigns"

router = SimpleRouter()
router.register(
    r"campaign_runners/simple", views.SimpleCampaignRunnerViewSet,
)
router.register(
    r"campaign_runners/interval", views.IntervalCampaignRunnerSerializerViewSet,
)
urlpatterns = []
