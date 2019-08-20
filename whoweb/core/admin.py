from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline

from whoweb.core.models import ModelEvent


class EventTabularInline(GenericTabularInline):
    model = ModelEvent
    fields = ("code", "message", "data", "start", "end", "created", "modified")
    readonly_fields = fields
    extra = 0
    can_delete = False


@admin.register(ModelEvent)
class ModelEventAdmin(admin.ModelAdmin):
    list_filter = ["content_type"]
