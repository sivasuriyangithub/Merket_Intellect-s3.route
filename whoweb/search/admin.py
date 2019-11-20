from admin_actions.admin import ActionsModelAdmin
from django.contrib import admin, messages
from django.contrib.admin import TabularInline
from django.shortcuts import redirect
from django.urls import reverse

from whoweb.core.admin import EventTabularInline
from whoweb.search.events import ENQUEUED_FROM_ADMIN
from whoweb.search.models import SearchExport, ScrollSearch
from whoweb.search.models.export import SearchExportPage


class SearchExportPageInline(TabularInline):
    model = SearchExportPage
    fields = ("page_num", "count", "created", "modified")
    readonly_fields = fields
    extra = 0

    def has_add_permission(self, request, obj=None):
        return False


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
    fields = (
        "seat",
        "uuid",
        "query",
        "status",
        "status_changed",
        "scroller",
        "charge",
        "notify",
        "on_trial",
        "progress_counter",
        "target",
        "sent",
        "sent_at",
        "charged",
        "refunded",
        "validation_list_id",
        "column_names",
    )
    readonly_fields = (
        "validation_list_id",
        "sent",
        "sent_at",
        "status_changed",
        "scroller",
        "column_names",
    )
    inlines = [EventTabularInline, SearchExportPageInline]
    actions_row = ("download",)
    actions_detail = ("run_publication_tasks", "download")

    def column_names(self, obj):
        return ", ".join(obj.get_column_names())

    column_names.short_description = "columns"

    def scroller(self, obj):
        if obj.scroll:
            link = reverse(
                "admin:search_scrollsearch_change", args=[obj.scroll.pk]
            )  # model name has to be lowercase
            return '<a href="%s">%s</a>' % (link, obj.scroll.scroll_key)
        return "None"

    scroller.allow_tags = True

    def download(self, request, pk):
        export = SearchExport.objects.get(pk=pk)
        return redirect(export.get_absolute_url())

    download.short_description = "💾️"

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

        export.log_event(
            evt=ENQUEUED_FROM_ADMIN, signatures=str(sigs), async_result=str(res)
        )
        return redirect(reverse("admin:search_searchexport_change", args=[pk]))

    run_publication_tasks.short_description = "Rerun"


@admin.register(ScrollSearch)
class ScrollSearchAdmin(ActionsModelAdmin):
    pass
