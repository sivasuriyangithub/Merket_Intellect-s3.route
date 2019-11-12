from admin_actions.admin import ActionsModelAdmin
from django.contrib import admin, messages
from django.shortcuts import redirect
from django.urls import reverse

from whoweb.core.admin import EventTabularInline
from whoweb.search.events import ENQUEUED_FROM_ADMIN
from whoweb.search.models import SearchExport


@admin.register(SearchExport)
class ExportAdmin(ActionsModelAdmin):
    list_display = (
        "pk",
        "uuid",
        "seat",
        "status",
        "progress_counter",
        "should_derive_email",
    )
    list_display_links = ("pk", "uuid")
    list_filter = ("status",)
    search_fields = ("seat__user__email", "seat__user__username")
    readonly_fields = (
        "validation_list_id",
        "sent",
        "sent_at",
        "status_changed",
        "scroll",
    )
    inlines = [EventTabularInline]
    # fields = ("validation_list_id", "sent", "sent_at", "with_invites")

    actions_detail = ("run_publication_tasks",)

    def run_publication_tasks(self, request, pk):
        export = SearchExport.objects.get(pk=pk)
        sigs = export.processing_signatures()
        res = sigs.apply_async()
        self.message_user(
            request,
            f"{export} successfully published. (Did not reset credits, flags, status, or counters first).",
            level=messages.SUCCESS,
        )
        self.message_user(request, f"Tasks run: {sigs}", level=messages.INFO)
        self.message_user(request, f"Result ID: {res}", level=messages.INFO)

        export.log_event(evt=ENQUEUED_FROM_ADMIN, signatures=sigs, async_result=res)
        return redirect(reverse("admin:search_searchexport_change", args=[pk]))

    run_publication_tasks.short_description = "Rerun"
