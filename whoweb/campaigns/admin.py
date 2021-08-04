from admin_actions.admin import ActionsModelAdmin
from django.conf import settings
from django.contrib import admin, messages
from django.db.models import F
from django.shortcuts import redirect
from django.template.defaultfilters import date
from django.urls import reverse
from django.utils import timezone
from django.utils.html import escape
from django.utils.safestring import mark_safe
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


def campaign_link(coldcampaign):
    link = reverse("admin:coldemail_coldcampaign_change", args=[coldcampaign.pk])
    return mark_safe(f'<a href="{link}">{escape(coldcampaign.__str__())}</a>')


def export_link(coldcampaign):
    export = coldcampaign.campaign_list.export
    link = reverse("admin:search_searchexport_change", args=[export.pk])
    return mark_safe(f'<a href="{link}">{escape(export.__str__())}</a>')


class SendingRuleInline(admin.TabularInline):
    model = SendingRule
    extra = 0


class DripRecordInline(InlineActionsMixin, admin.TabularInline):
    model = DripRecord
    extra = 0
    can_delete = False
    fields = (
        "root",
        "drip_campaign",
        "export",
        "order",
    )
    readonly_fields = ("root", "drip_campaign", "order", "export")
    inline_actions = [
        "rerun_drip",
    ]

    def has_add_permission(self, request, obj=None):
        return False

    def drip_campaign(self, obj: BaseCampaignRunner.drips.through):
        return campaign_link(obj.drip)

    drip_campaign.short_description = "Drip"

    def export(self, obj: BaseCampaignRunner.drips.through):
        return export_link(obj.drip)

    def rerun_drip(
        self,
        request,
        obj: BaseCampaignRunner.drips.through,
        parent_obj: BaseCampaignRunner = None,
    ):
        cold_campaign = obj.drip
        export = cold_campaign.campaign_list.export
        if export.status != export.ExportStatusOptions.COMPLETE:
            messages.add_message(
                request, messages.ERROR, f"Export must be completed to rerun campaign."
            )

        cold_campaign.status = ColdCampaign.CampaignObjectStatusOptions.CREATED
        cold_campaign.save()
        publish_sigs = parent_obj.publish_drip(
            root_campaign=obj.root, following=None, using_existing=cold_campaign
        )
        messages.add_message(
            request, messages.SUCCESS, f"{cold_campaign} successfully republished.",
        )
        messages.add_message(request, messages.INFO, f"Result ID: {publish_sigs}")
        change_url = reverse(
            "admin:{}_{}_change".format(
                parent_obj._meta.app_label, parent_obj._meta.model_name,
            ),
            args=[parent_obj.pk],
        )
        return redirect(change_url)


class RootCampaignInline(InlineActionsMixin, admin.TabularInline):
    model = BaseCampaignRunner.campaigns.through
    extra = 0
    can_delete = False
    inline_actions = [
        "rerun",
    ]
    fields = ("campaign", "campaign__status", "campaign__status_changed", "export")
    readonly_fields = (
        "campaign",
        "campaign__status",
        "campaign__status_changed",
        "export",
    )

    verbose_name = "Cold Campaign (root)"
    verbose_name_plural = "Cold Campaigns (roots)"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            campaign__status=F("coldcampaign__status"),
            campaign__status_changed=F("coldcampaign__status_changed"),
        )

    def campaign(self, obj: BaseCampaignRunner.campaigns.through):
        return campaign_link(obj.coldcampaign)

    campaign.short_description = "Cold Campaign"

    def campaign__status(self, obj):
        return ColdCampaign.CampaignObjectStatusOptions(obj.campaign__status).name

    def campaign__status_changed(self, obj):
        return date(
            timezone.localtime(obj.campaign__status_changed), settings.DATETIME_FORMAT
        )

    def export(self, obj: BaseCampaignRunner.campaigns.through):
        return export_link(obj.coldcampaign)

    export.short_description = "Export"

    def has_add_permission(self, request, obj=None):
        return False

    def rerun(self, request, obj, parent_obj=None):
        cold_campaign = obj.coldcampaign
        export = cold_campaign.campaign_list.export
        if export.status != export.ExportStatusOptions.COMPLETE:
            messages.add_message(
                request, messages.ERROR, f"Export must be completed to rerun campaign."
            )

        runner = parent_obj
        runner.run_id = None
        runner.save()
        cold_campaign.status = ColdCampaign.CampaignObjectStatusOptions.CREATED
        cold_campaign.save()
        sigs, campaign = runner.publish(apply_tasks=False, using_existing=cold_campaign)
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
            "StatusOptions Fields",
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
            "StatusOptions Fields",
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
