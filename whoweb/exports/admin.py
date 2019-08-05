from django.contrib import admin
from django.contrib.auth import get_user_model

from whoweb.exports.models import SearchExport


@admin.register(SearchExport)
class ExportAdmin(admin.ModelAdmin):

    pass
