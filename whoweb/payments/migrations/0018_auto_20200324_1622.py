# Generated by Django 2.2.8 on 2020-03-24 23:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("djstripe", "0005_2_2"),
        ("payments", "0017_auto_20200319_1653"),
    ]

    operations = [
        migrations.CreateModel(
            name="MultiPlanCustomer",
            fields=[],
            options={"proxy": True, "indexes": [], "constraints": [],},
            bases=("djstripe.customer",),
        )
    ]
