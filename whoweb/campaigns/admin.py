from admin_actions.admin import ActionsModelAdmin
from django.contrib import admin

from whoweb.core.admin import EventTabularInline
from .models import SimpleDripCampaignRunner, IntervalCampaignRunner


@admin.register(SimpleDripCampaignRunner)
class SimpleDripCampaignRunnerAdmin(ActionsModelAdmin):
    inlines = [EventTabularInline]


@admin.register(IntervalCampaignRunner)
class IntervalCampaignRunnerAdmin(ActionsModelAdmin):
    inlines = [EventTabularInline]
