from django.conf import settings
from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline
from django.conf.locale.en import formats as en_formats

from whoweb.core.models import ModelEvent


class EventTabularInline(GenericTabularInline):
    model = ModelEvent
    fields = ("code", "message", "data", "start", "end", "created", "modified")
    readonly_fields = fields
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ModelEvent)
class ModelEventAdmin(admin.ModelAdmin):
    list_filter = ["content_type"]


admin.site.site_url = "/ww/api"
admin.site.site_header = "Whoweb Administration"

en_formats.DATETIME_FORMAT = settings.DATETIME_FORMAT
