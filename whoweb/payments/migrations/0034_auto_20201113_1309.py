# Generated by Django 2.2.10 on 2020-11-13 21:09

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("auth", "0011_update_proxy_permissions"),
        ("payments", "0033_billingaccountinvitation"),
    ]

    operations = [
        migrations.AddField(
            model_name="wkplan",
            name="permission_group",
            field=models.ForeignKey(
                help_text="Permissions group users will be placed in when on an active subscription to this plan.",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to="auth.Group",
            ),
        ),
        migrations.AddField(
            model_name="wkplanpreset",
            name="permission_group",
            field=models.ForeignKey(
                help_text="Permissions group users will be placed in when on an active subscription to this plan.",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to="auth.Group",
            ),
        ),
        migrations.CreateModel(
            name="BillingPermissionGrant",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "permission_group",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="auth.Group"
                    ),
                ),
                (
                    "plan",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="permission_grants",
                        to="payments.WKPlan",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="billing_permission_grants",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]
