# Generated by Django 2.2.8 on 2020-03-13 19:21

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0015_wkplanpreset"),
        ("search", "0023_auto_20200313_1220"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="derivationcache", unique_together={("profile_id", "billing_seat")},
        ),
        migrations.RemoveField(model_name="derivationcache", name="seat",),
    ]