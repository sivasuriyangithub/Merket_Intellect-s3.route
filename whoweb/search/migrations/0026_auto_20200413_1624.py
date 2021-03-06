# Generated by Django 2.2.8 on 2020-04-13 23:24

from django.db import migrations, models
import whoweb.search.models.export


class Migration(migrations.Migration):

    dependencies = [
        ("search", "0025_auto_20200413_1501"),
    ]

    operations = [
        migrations.AlterField(
            model_name="searchexport",
            name="csv",
            field=models.FileField(
                blank=True,
                null=True,
                upload_to=whoweb.search.models.export.download_file_location,
            ),
        ),
        migrations.AlterField(
            model_name="searchexport",
            name="pre_validation_file",
            field=models.FileField(
                blank=True,
                editable=False,
                null=True,
                upload_to=whoweb.search.models.export.validation_file_location,
            ),
        ),
    ]
