# Generated by Django 2.2.19 on 2021-07-16 18:02

from django.db import migrations, models
import whoweb.coldemail.models.base


class Migration(migrations.Migration):

    dependencies = [
        ("coldemail", "0022_auto_20210702_1246"),
    ]

    operations = [
        migrations.AlterField(
            model_name="campaignlist",
            name="status",
            field=models.IntegerField(
                blank=True,
                choices=[
                    (0, "CREATED"),
                    (2, "PENDING"),
                    (4, "PUBLISHED"),
                    (8, "PAUSED"),
                ],
                db_index=True,
                default=whoweb.coldemail.models.base.ColdemailBaseModel.CampaignObjectStatusOptions(
                    0
                ),
                verbose_name="status",
            ),
        ),
        migrations.AlterField(
            model_name="campaignmessage",
            name="status",
            field=models.IntegerField(
                blank=True,
                choices=[
                    (0, "CREATED"),
                    (2, "PENDING"),
                    (4, "PUBLISHED"),
                    (8, "PAUSED"),
                ],
                db_index=True,
                default=whoweb.coldemail.models.base.ColdemailBaseModel.CampaignObjectStatusOptions(
                    0
                ),
                verbose_name="status",
            ),
        ),
        migrations.AlterField(
            model_name="coldcampaign",
            name="status",
            field=models.IntegerField(
                blank=True,
                choices=[
                    (0, "CREATED"),
                    (2, "PENDING"),
                    (4, "PUBLISHED"),
                    (8, "PAUSED"),
                ],
                db_index=True,
                default=whoweb.coldemail.models.base.ColdemailBaseModel.CampaignObjectStatusOptions(
                    0
                ),
                verbose_name="status",
            ),
        ),
        migrations.AlterField(
            model_name="singlecoldemail",
            name="status",
            field=models.IntegerField(
                blank=True,
                choices=[
                    (0, "CREATED"),
                    (2, "PENDING"),
                    (4, "PUBLISHED"),
                    (8, "PAUSED"),
                ],
                db_index=True,
                default=whoweb.coldemail.models.base.ColdemailBaseModel.CampaignObjectStatusOptions(
                    0
                ),
                verbose_name="status",
            ),
        ),
    ]
