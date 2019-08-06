from django.contrib import admin
from django.contrib.auth import get_user_model

from whoweb.exports.models import SearchExport


@admin.register(SearchExport)
class ExportAdmin(admin.ModelAdmin):
    list_display = ("pk", "uuid", "user", "status", "progress_counter", "notify")
    list_display_links = ("pk", "uuid")
    list_filter = ("status",)
    readonly_fields = ("validation_list_id", "sent", "sent_at", "with_invites")
    # fields = ("validation_list_id", "sent", "sent_at", "with_invites")
