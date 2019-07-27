from django.urls import path

from whoweb.coldemail.views import replyto_webhook_view

app_name = "users"
urlpatterns = [
    path("<str:match_id>/", view=replyto_webhook_view, name="reply_forwarding_webhook")
]
