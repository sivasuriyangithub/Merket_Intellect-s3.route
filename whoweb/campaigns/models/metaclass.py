from django.db import models

from whoweb.coldemail.models import CampaignMessage, ColdCampaign


def Messages(rule_class):
    return models.ManyToManyField(CampaignMessage, through=rule_class,)


def Drips(drip_record_class):
    return models.ManyToManyField(
        ColdCampaign,
        related_name="+",
        through=drip_record_class,
        through_fields=("manager", "drip"),
    )
