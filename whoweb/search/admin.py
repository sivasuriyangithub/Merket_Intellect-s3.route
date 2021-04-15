import datetime

from admin_actions.admin import ActionsModelAdmin
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.admin import TabularInline
from django.contrib.admin.options import IncorrectLookupParameters
from django.contrib.humanize.templatetags.humanize import naturaltime
from django.core.exceptions import ValidationError
from django.db.models import Sum, Max, Case, When, DateTimeField, Value
from django.shortcuts import redirect
from django.template.defaultfilters import date
from django.urls import reverse
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.utils.timezone import localtime
from django.utils.translation import gettext_lazy as _

from whoweb.core.admin import EventTabularInline
from whoweb.search.events import ENQUEUED_FROM_ADMIN
from whoweb.search.models import SearchExport, ScrollSearch, FilterValueList
from whoweb.search.models.export import SearchExportPage

epoch = datetime.datetime(1970, 1, 1, 0, 0, 0, tzinfo=timezone.get_default_timezone())


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
        link = reverse("admin:search_searchexportpage_change", args=[obj.pk])
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
        link = reverse("admin:search_searchexport_change", args=[obj.export_id])
        return '<a href="%s">%s</a>' % (link, obj.export)

    export_link.short_description = "Export"


class LatestPageModificationFilter(admin.SimpleListFilter):
    title = "Latest Page Update Time"
    parameter_name = "_latest_page_modified"

    def __init__(self, request, params, model, model_admin):
        self.field_generic = "%s__" % self.parameter_name

        self.date_params = {
            k: v for k, v in params.items() if k.startswith(self.field_generic)
        }

        now = timezone.now()
        # When time zone support is enabled, convert "now" to the user's time
        # zone so Django's definition of "Today" matches what the user expects.
        if timezone.is_aware(now):
            now = timezone.localtime(now)
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)

        self.lookup_kwarg_since = "%s__gte" % self.parameter_name
        self.lookup_kwarg_until = "%s__lt" % self.parameter_name
        self.links = (
            (_("Any date"), {}),
            (
                _("Today"),
                {
                    self.lookup_kwarg_since: str(today),
                    self.lookup_kwarg_until: str(today + datetime.timedelta(days=1)),
                },
            ),
            (
                _("Yesterday"),
                {
                    self.lookup_kwarg_since: str(today - datetime.timedelta(days=1)),
                    self.lookup_kwarg_until: str(today),
                },
            ),
            (
                _("1-2 days ago"),
                {
                    self.lookup_kwarg_since: str(today - datetime.timedelta(days=2)),
                    self.lookup_kwarg_until: str(today - datetime.timedelta(days=1)),
                },
            ),
            (
                _("2-3 days ago"),
                {
                    self.lookup_kwarg_since: str(today - datetime.timedelta(days=3)),
                    self.lookup_kwarg_until: str(today - datetime.timedelta(days=2)),
                },
            ),
            (
                _("More than 7 days ago"),
                {self.lookup_kwarg_until: str(today - datetime.timedelta(days=7)),},
            ),
        )
        super().__init__(request, params, model, model_admin)

    def lookups(self, request, model_admin):
        return self.links

    def choices(self, changelist):
        for title, param_dict in self.links:
            yield {
                "selected": self.date_params == param_dict,
                "query_string": changelist.get_query_string(
                    param_dict, [self.field_generic]
                ),
                "display": title,
            }

    def expected_parameters(self):
        params = [self.lookup_kwarg_since, self.lookup_kwarg_until]
        return params

    def queryset(self, request, queryset):
        try:
            return queryset.filter(**self.used_parameters)
        except (ValueError, ValidationError) as e:
            # Fields may raise a ValueError or ValidationError when converting
            # the parameters to the correct type.
            raise IncorrectLookupParameters(e)


@admin.register(SearchExport)
class ExportAdmin(ActionsModelAdmin):
    list_display = (
        "pk",
        "uuid",
        "billing_seat",
        "status",
        "rows_enqueued",
        "latest_page_modified",
        "progress_counter",
        "target",
        "rows_uploaded",
        "should_derive_email",
    )
    list_display_links = (
        "pk",
        "uuid",
    )
    list_per_page = 10
    list_filter = (
        "status",
        "charge",
        "created",
        "modified",
        LatestPageModificationFilter,
    )
    search_fields = (
        "seat__user__email",
        "seat__user__username",
        "billing_seat__user__email",
        "billing_seat__user__username",
        "pk",
        "uuid",
    )
    fieldsets = (
        (None, {"fields": ("uuid", "billing_seat", "query", "scroller",)}),
        (
            "Status Fields",
            {
                "classes": (),
                "fields": (
                    ("status", "status_changed",),
                    ("progress_counter", "target",),
                    "queue_priority",
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
                "fields": (("charge", "notify", "on_trial"), "column_names",),
            },
        ),
    )
    readonly_fields = (
        "sent",
        "sent_at",
        "working_count",
        "rows_enqueued",
        "queue_priority",
        "latest_page_modified",
        "status_changed",
        "scroller",
        "column_names",
    )
    inlines = [EventTabularInline, SearchExportPageInline]
    actions_row = ("download", "download_json")
    actions_detail = ("run_publication_tasks", "download", "download_json")
    actions = ("store_validation_results", "compute_rows_uploaded")

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .annotate(
                _working_count=Sum("pages__progress_counter"),
                _rows_enqueued=Sum("pages__pending_count"),
                _page_modified=Max("pages__modified"),
            )
            .annotate(
                _latest_page_modified=Case(
                    When(_page_modified__isnull=False, then="_page_modified"),
                    default=Value(epoch),  # sorts null to bottom
                    output_field=DateTimeField(),
                )
            )
        )

    def working_count(self, obj):
        return obj._working_count

    working_count.short_description = "Working Rows"

    def rows_enqueued(self, obj):
        return obj._rows_enqueued

    rows_enqueued.admin_order_field = "_rows_enqueued"

    def latest_page_modified(self, obj):
        return (
            "n/a"
            if obj._latest_page_modified == epoch
            else "{} ({})".format(
                date(localtime(obj._latest_page_modified), settings.DATETIME_FORMAT),
                naturaltime(obj._latest_page_modified),
            )
        )

    latest_page_modified.admin_order_field = "_latest_page_modified"

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
        export = SearchExport.available_objects.get(pk=pk)
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

    def compute_rows_uploaded(self, request, queryset):
        for export in queryset:
            if export.status != SearchExport.STATUS.complete:
                self.message_user(
                    request,
                    f"Could not set row count of {export}, export is not complete.",
                    level=messages.WARNING,
                )
                continue
            if export.rows_uploaded > 0:
                self.message_user(
                    request, f"{export} row count already set.", level=messages.INFO,
                )
                continue
            row_count = 0
            for _ in export.generate_csv_rows():
                row_count += 1
            export.rows_uploaded = row_count
            export.save()
            self.message_user(
                request, f"Set row count of {export}.", level=messages.SUCCESS,
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


@admin.register(FilterValueList)
class FilterValueListAdmin(ActionsModelAdmin):
    fields = (
        "name",
        "description",
        "type",
        "tags",
        "values",
        "billing_seat",
    )
