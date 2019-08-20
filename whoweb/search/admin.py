from django.contrib import admin

from whoweb.core.admin import EventTabularInline
from whoweb.search.models import SearchExport


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
    readonly_fields = (
        "validation_list_id",
        "sent",
        "sent_at",
        "status_changed",
        "scroll",
    )
    inlines = [EventTabularInline]
    # fields = ("validation_list_id", "sent", "sent_at", "with_invites")
