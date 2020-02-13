from django.urls import path
from rest_framework.routers import SimpleRouter
from . import views
from whoweb.coldemail.views import replyto_webhook_view

app_name = "coldemail"

router = SimpleRouter()
router.register(r"campaign/messages", views.CampaignMessageViewSet)
router.register(r"campaign/message_templates", views.CampaignMessageTemplateViewSet)
router.register(r"single_emails", views.SingleEmailViewSet)
router.register(r"campaign/lists", views.CampaignListViewSet)

urlpatterns = [
    path("<str:match_id>/", view=replyto_webhook_view, name="reply_forwarding_webhook")
]
