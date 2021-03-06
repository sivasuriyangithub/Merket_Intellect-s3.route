# Generated by Django 2.2.6 on 2019-11-23 00:58

from django.db import migrations, models
import django.utils.timezone
import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [("search", "0005_auto_20191120_2231")]

    operations = [
        migrations.AddField(
            model_name="searchexportpage",
            name="status_changed",
            field=model_utils.fields.MonitorField(
                default=django.utils.timezone.now,
                monitor="status",
                verbose_name="status changed",
            ),
        ),
        migrations.AddField(
            model_name="searchexportpage",
            name="status",
            field=models.IntegerField(
                blank=True,
                choices=[(0, "Created"), (2, "Running"), (4, "Complete")],
                default=0,
                verbose_name="status",
            ),
        ),
    ]
