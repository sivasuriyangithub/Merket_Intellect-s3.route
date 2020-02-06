from django.contrib import admin
from .models import SimpleDripCampaignRunner, IntervalCampaignRunner


admin.site.register(SimpleDripCampaignRunner, admin.ModelAdmin)
admin.site.register(IntervalCampaignRunner, admin.ModelAdmin)
