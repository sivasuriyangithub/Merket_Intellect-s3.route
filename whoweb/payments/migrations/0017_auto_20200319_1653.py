# Generated by Django 2.2.8 on 2020-03-19 23:53

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0016_wkplanpreset_trial_days_allows"),
    ]

    operations = [
        migrations.RenameField(
            model_name="wkplanpreset",
            old_name="trial_days_allows",
            new_name="trial_days_allowed",
        ),
    ]
