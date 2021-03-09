from admin_actions.admin import ActionsModelAdmin
from django.conf import settings
from django.contrib import admin, messages
from django.db.models import F
from django.shortcuts import redirect
from django.template.defaultfilters import date
from django.urls import reverse
from django.utils import timezone
from inline_actions.admin import InlineActionsMixin, InlineActionsModelAdminMixin

from whoweb.campaigns.events import ENQUEUED_FROM_ADMIN
from whoweb.coldemail.models import ColdCampaign
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


class RootCampaignInline(InlineActionsMixin, admin.TabularInline):
    model = BaseCampaignRunner.campaigns.through
    extra = 0
    can_delete = False
    inline_actions = [
        "rerun",
    ]
    fields = (
        "coldcampaign",
        "campaign__status",
        "campaign__status_changed",
    )
    readonly_fields = ("campaign__status", "campaign__status_changed")

    verbose_name = "Cold Campaign (root)"
    verbose_name_plural = "Cold Campaigns (roots)"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            campaign__status=F("coldcampaign__status"),
            campaign__status_changed=F("coldcampaign__status_changed"),
        )

    def campaign__status(self, obj):
        return ColdCampaign.STATUS[obj.campaign__status]

    def campaign__status_changed(self, obj):
        return date(
            timezone.localtime(obj.campaign__status_changed), settings.DATETIME_FORMAT
        )

    def has_add_permission(self, request, obj=None):
        return False

    def rerun(self, request, obj, parent_obj=None):
        cold_campaign = obj.coldcampaign
        export = cold_campaign.campaign_list.export
        if export.status != export.STATUS.complete:
            messages.add_message(
                request, messages.ERROR, f"Export must be completed to rerun campaign."
            )

        runner = parent_obj
        runner.run_id = None
        runner.save()
        cold_campaign.status = ColdCampaign.STATUS.created
        cold_campaign.save()
        sigs, campaign = runner.publish(apply_tasks=False, with_campaign=cold_campaign)
        res = sigs.apply_async()
        messages.add_message(
            request,
            messages.SUCCESS,
            f"{runner} successfully republished starting at {campaign}.",
        )
        messages.add_message(request, messages.INFO, f"Tasks run: {sigs}")
        messages.add_message(request, messages.INFO, f"Result ID: {res}")
        runner.log_event(
            evt=ENQUEUED_FROM_ADMIN, signatures=str(sigs), async_result=str(res)
        )
        change_url = reverse(
            "admin:{}_{}_change".format(
                runner._meta.app_label, runner._meta.model_name,
            ),
            args=[runner.pk],
        )
        return redirect(change_url)


@admin.register(SimpleDripCampaignRunner)
class SimpleDripCampaignRunnerAdmin(InlineActionsModelAdminMixin, ActionsModelAdmin):
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
    search_fields = (
        "seat__user__email",
        "seat__user__username",
        "pk__exact",
        "public_id",
    )

    fieldsets = (
        (
            None,
            {
                "fields": (
                    ("pk", "public_id",),
                    "billing_seat",
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
                    "published",
                ),
            },
        ),
    )
    readonly_fields = ("pk", "status_changed", "scroll", "published", "public_id")


@admin.register(IntervalCampaignRunner)
class IntervalCampaignRunnerAdmin(InlineActionsModelAdminMixin, ActionsModelAdmin):
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
    search_fields = (
        "seat__user__email",
        "seat__user__username",
        "pk__exact",
        "public_id",
    )

    fieldsets = (
        (
            None,
            {
                "fields": (
                    ("pk", "public_id",),
                    "billing_seat",
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
                    "published",
                ),
            },
        ),
    )
    readonly_fields = ("pk", "status_changed", "scroll", "published", "public_id")
