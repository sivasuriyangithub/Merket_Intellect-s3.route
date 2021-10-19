# Generated by Django 2.2.19 on 2021-09-09 18:36

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("campaigns", "0023_auto_20210909_1134"),
    ]

    operations = [
        migrations.AlterField(
            model_name="icebreakertemplate",
            name="billing_seat",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="payments.BillingAccountMember",
            ),
        ),
    ]