from admin_actions.admin import ActionsModelAdmin
from django.contrib import admin

from whoweb.core.admin import EventTabularInline
from .models import (
    SimpleDripCampaignRunner,
    IntervalCampaignRunner,
    SendingRule,
    DripRecord,
    BaseCampaignRunner,
)


class SendingRuleInline(admin.TabularInline):
    model = SendingRule
    extra = 0


class DripRecordInline(admin.TabularInline):
    model = DripRecord
    extra = 0
    can_delete = False
    readonly_fields = ("root", "drip", "order")

    def has_add_permission(self, request, obj=None):
        return False


class RootCampaignInline(admin.TabularInline):
    model = BaseCampaignRunner.campaigns.through
    extra = 0
    can_delete = False

    verbose_name = "Cold Campaign (root)"
    verbose_name_plural = "Cold Campaigns (roots)"

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(SimpleDripCampaignRunner)
class SimpleDripCampaignRunnerAdmin(ActionsModelAdmin):
    inlines = [
        SendingRuleInline,
        RootCampaignInline,
        DripRecordInline,
        EventTabularInline,
    ]

    list_display = (
        "pk",
        "public_id",
        "title",
        "status",
        "budget",
        "status_changed",
        "created",
    )
    list_display_links = (
        "pk",
        "public_id",
    )
    list_filter = (
        "status",
        "created",
        "modified",
    )
    search_fields = ("seat__user__email", "seat__user__username", "pk", "public_id")

    fieldsets = (
        (
            None,
            {
                "fields": (
                    ("pk", "public_id",),
                    "seat",
                    "title",
                    "query",
                    "budget",
                    "tracking_params",
                    "use_credits_method",
                    "open_credit_budget",
                    "tags",
                )
            },
        ),
        (
            "Status Fields",
            {
                "classes": (),
                "fields": (
                    ("status", "status_changed",),
                    "run_id",
                    "scroll",
                    "published_at",
                ),
            },
        ),
    )
    readonly_fields = ("pk", "status_changed", "scroll", "published_at", "public_id")


@admin.register(IntervalCampaignRunner)
class IntervalCampaignRunnerAdmin(ActionsModelAdmin):
    inlines = [
        SendingRuleInline,
        RootCampaignInline,
        DripRecordInline,
        EventTabularInline,
    ]

    list_display = (
        "pk",
        "public_id",
        "title",
        "status",
        "budget",
        "status_changed",
        "created",
    )
    list_display_links = (
        "pk",
        "public_id",
    )
    list_filter = (
        "status",
        "created",
        "modified",
    )
    search_fields = ("seat__user__email", "seat__user__username", "pk", "public_id")

    fieldsets = (
        (
            None,
            {
                "fields": (
                    ("pk", "public_id",),
                    "seat",
                    "title",
                    "query",
                    "budget",
                    "tracking_params",
                    "interval_hours",
                    "max_sends",
                    "tags",
                )
            },
        ),
        (
            "Status Fields",
            {
                "classes": (),
                "fields": (
                    ("status", "status_changed",),
                    "run_id",
                    "scroll",
                    "published_at",
                ),
            },
        ),
    )
    readonly_fields = ("pk", "status_changed", "scroll", "published_at", "public_id")
