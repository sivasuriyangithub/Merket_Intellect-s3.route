# Generated by Django 2.2.6 on 2019-11-19 23:17

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("search", "0003_auto_20191114_2326")]

    operations = [
        migrations.RemoveField(model_name="searchexport", name="columns"),
        migrations.AlterField(
            model_name="searchexport",
            name="status",
            field=models.IntegerField(
                blank=True,
                choices=[
                    (0, "Created"),
                    (2, "Pages Running"),
                    (4, "Pages Complete"),
                    (8, "Awaiting External Validation"),
                    (16, "Validation Complete"),
                    (32, "Post Processing Hooks Done"),
                    (128, "Export Complete"),
                ],
                db_index=True,
                default=0,
                verbose_name="status",
            ),
        ),
        migrations.AlterField(
            model_name="searchexportpage",
            name="working_data",
            field=django.contrib.postgres.fields.jsonb.JSONField(
                default={}, editable=False, null=True
            ),
        ),
    ]