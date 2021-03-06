# Generated by Django 2.2.8 on 2020-02-27 23:46

import django.contrib.postgres.fields.jsonb
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("search", "0017_derivationcache"),
    ]

    operations = [
        migrations.AddField(
            model_name="derivationcache",
            name="emails",
            field=django.contrib.postgres.fields.jsonb.JSONField(default=list),
        ),
        migrations.AddField(
            model_name="derivationcache",
            name="phones",
            field=django.contrib.postgres.fields.jsonb.JSONField(default=list),
        ),
    ]
