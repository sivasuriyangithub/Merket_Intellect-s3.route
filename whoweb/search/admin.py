from admin_actions.admin import ActionsModelAdmin
from django.contrib import admin, messages
from django.contrib.admin import TabularInline
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.safestring import mark_safe

from whoweb.core.admin import EventTabularInline
from whoweb.search.events import ENQUEUED_FROM_ADMIN
from whoweb.search.models import SearchExport, ScrollSearch
from whoweb.search.models.export import SearchExportPage


class SearchExportPageInline(TabularInline):
    model = SearchExportPage
    fields = (
        "export_link",
        "status",
        "pending_count",
        "progress_counter",
        "final_count",
        "created",
        "modified",
    )
    readonly_fields = fields
    extra = 0

    def get_queryset(self, request):
        return super().get_queryset(request).defer("data")

    def has_add_permission(self, request, obj=None):
        return False

    def final_count(self, obj):
        return obj.count

    @mark_safe
    def export_link(self, obj: SearchExportPage):
        link = reverse(
            "admin:search_searchexportpage_change", args=[obj.pk]
        )  # model name has to be lowercase
        return '<a href="%s">Page %s</a>' % (link, obj.page_num)

    export_link.short_description = "Page num"


@admin.register(SearchExportPage)
class SearchExportPageAdmin(ActionsModelAdmin):
    list_display = (
        "pk",
        "export",
        "page_num",
        "created",
        "modified",
        "status",
        "count",
    )
    list_display_links = ("export",)
    list_filter = ("status", "created")
    search_fields = ("export__uuid", "export__pk")
    fields = (
        "export_link",
        "page_num",
        "created",
        "modified",
        "status",
        "count",
        "pending_count",
        "progress_counter",
    )
    readonly_fields = fields

    def get_queryset(self, request):
        return super().get_queryset(request).defer("data")

    @mark_safe
    def export_link(self, obj: SearchExportPage):
        link = reverse(
            "admin:search_searchexport_change", args=[obj.export_id]
        )  # model name has to be lowercase
        return '<a href="%s">%s</a>' % (link, obj.export)

    export_link.short_description = "Export"


@admin.register(SearchExport)
class ExportAdmin(ActionsModelAdmin):
    list_display = (
        "pk",
        "uuid",
        "seat",
        "status",
        "target",
        "should_derive_email",
    )
    list_display_links = (
        "pk",
        "uuid",
    )
    list_filter = ("status", "charge")
    search_fields = ("seat__user__email", "seat__user__username", "pk", "uuid")
    fieldsets = (
        (None, {"fields": ("uuid", "seat", "query", "scroller",)}),
        (
            "Status Fields",
            {
                "fields": (
                    ("status", "status_changed",),
                    ("progress_counter", "target",),
                    "rows_enqueued",
                    "working_count",
                    "latest_page_modified",
                    ("sent", "sent_at",),
                    "validation_list_id",
                ),
            },
        ),
        (
            "Behavior Fields",
            {
                "classes": ("collapse",),
                "fields": (("charge", "notify", "on_trial"), "column_names"),
            },
        ),
    )
    readonly_fields = (
        "sent",
        "sent_at",
        "working_count",
        "rows_enqueued",
        "latest_page_modified",
        "status_changed",
        "scroller",
        "column_names",
    )
    inlines = [EventTabularInline, SearchExportPageInline]
    actions_row = ("download", "download_json")
    actions_detail = ("run_publication_tasks", "download", "download_json")
    actions = ("store_validation_results",)

    def working_count(self, obj: SearchExport):
        return sum(page.progress_counter for page in obj.pages.all())

    working_count.short_description = "Working progress count"

    def rows_enqueued(self, obj: SearchExport):
        return sum(page.pending_count for page in obj.pages.all())

    def latest_page_modified(self, obj: SearchExport):
        return obj.pages.order_by("-modified").first().modified

    def column_names(self, obj):
        return ", ".join(obj.get_column_names())

    column_names.short_description = "columns"

    @mark_safe
    def scroller(self, obj):
        if obj.scroll:
            link = reverse(
                "admin:search_scrollsearch_change", args=[obj.scroll.pk]
            )  # model name has to be lowercase
            return '<a href="%s">%s</a>' % (link, obj.scroll.scroll_key)
        return "None"

    def download(self, request, pk):
        export = SearchExport.objects.get(pk=pk)
        return redirect(export.get_absolute_url())

    download.short_description = "💾.csv"

    def download_json(self, request, pk):
        export = SearchExport.objects.get(pk=pk)
        return redirect(export.get_absolute_url("json"))

    download_json.short_description = "💾.json"

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

    def store_validation_results(self, request, queryset):
        for export in queryset:
            results = export.get_validation_results(only_valid=True)
            self.message_user(
                request, f"Downloaded validation for {export}.", level=messages.SUCCESS
            )
            export.apply_validation_to_profiles_in_pages(validation=results)
            self.message_user(
                request,
                f"Updated profiles in page data of {export} with validation results.",
                level=messages.SUCCESS,
            )


@admin.register(ScrollSearch)
class ScrollSearchAdmin(ActionsModelAdmin):
    fields = (
        "scroll_key",
        "scroll_key_modified",
        "page_size",
        "query_hash",
        "total",
        "query_serialized",
    )
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False

    def query_serialized(self, obj):
        return obj.query.serialize()

    query_serialized.short_description = "query"
