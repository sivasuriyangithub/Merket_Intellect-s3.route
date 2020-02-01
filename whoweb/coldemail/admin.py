from django.contrib import admin
from .models import (
    ColdCampaign,
    CampaignMessage,
    CampaignMessageTemplate,
    CampaignList,
    SingleColdEmail,
)


admin.site.register(ColdCampaign, admin.ModelAdmin)
admin.site.register(CampaignMessage, admin.ModelAdmin)
admin.site.register(CampaignMessageTemplate, admin.ModelAdmin)
admin.site.register(CampaignList, admin.ModelAdmin)
admin.site.register(SingleColdEmail, admin.ModelAdmin)
