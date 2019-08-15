from django.contrib import admin
from django.contrib.auth import get_user_model

from whoweb.exports.models import SearchExport


@admin.register(SearchExport)
class ExportAdmin(admin.ModelAdmin):
    list_display = (
        "pk",
        "uuid",
        "user",
        "status",
        "progress_counter",
        "should_derive_email",
    )
    list_display_links = ("pk", "uuid")
    list_filter = ("status",)
    search_fields = ("user__email", "user__username")
    readonly_fields = ("validation_list_id", "sent", "sent_at")
    # fields = ("validation_list_id", "sent", "sent_at", "with_invites")
