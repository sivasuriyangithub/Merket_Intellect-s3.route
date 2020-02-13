from rest_framework.routers import SimpleRouter

from . import views

app_name = "campaigns"

router = SimpleRouter()
router.register(
    r"campaign/simple", views.SimpleCampaignViewSet,
)
router.register(
    r"campaign/interval", views.IntervalCampaignSerializerViewSet,
)
urlpatterns = []
