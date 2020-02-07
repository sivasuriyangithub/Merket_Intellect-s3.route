from django.urls import path
from rest_framework.routers import SimpleRouter
from . import views
from whoweb.coldemail.views import replyto_webhook_view

app_name = "coldemail"

router = SimpleRouter()
router.register(r"campaign_messages", views.CampaignMessageViewSet)
router.register(r"campaigns", views.CampaignViewSet)
router.register(r"campaign_lists", views.CampaignListViewSet)

urlpatterns = [
    path("<str:match_id>/", view=replyto_webhook_view, name="reply_forwarding_webhook")
]
