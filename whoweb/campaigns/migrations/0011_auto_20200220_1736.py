# Generated by Django 2.2.8 on 2020-02-21 01:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("campaigns", "0010_remove_simpledripcampaignrunner_preset_campaign_list"),
    ]

    operations = [
        migrations.AlterField(
            model_name="basecampaignrunner",
            name="campaigns",
            field=models.ManyToManyField(to="coldemail.ColdCampaign"),
        ),
    ]
