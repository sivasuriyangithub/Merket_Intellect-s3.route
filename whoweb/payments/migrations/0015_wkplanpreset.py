# Generated by Django 2.2.8 on 2020-03-12 03:23

from django.db import migrations, models
import whoweb.contrib.fields


class Migration(migrations.Migration):

    dependencies = [
        ("djstripe", "0005_2_2"),
        ("payments", "0014_delete_wkplanpreset"),
    ]

    operations = [
        migrations.CreateModel(
            name="WKPlanPreset",
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
                    "public_id",
                    models.CharField(
                        default=whoweb.contrib.fields.random_public_id,
                        editable=False,
                        help_text="Public ID of the object.",
                        max_length=16,
                        unique=True,
                        verbose_name="ID",
                    ),
                ),
                (
                    "credits_per_enrich",
                    models.IntegerField(
                        default=5,
                        help_text="Number of credits charged for an enrich service call.",
                        verbose_name="Credits per Enrich",
                    ),
                ),
                (
                    "credits_per_work_email",
                    models.IntegerField(
                        default=100,
                        help_text="Number of credits charged for a service call returning any work emails.",
                        verbose_name="Credits per Work Derivation",
                    ),
                ),
                (
                    "credits_per_personal_email",
                    models.IntegerField(
                        default=300,
                        help_text="Number of credits charged for a service call returning any personal emails.",
                        verbose_name="Credits per Personal Derivation",
                    ),
                ),
                (
                    "credits_per_phone",
                    models.IntegerField(
                        default=400,
                        help_text="Number of credits charged for a service call returning any phone numbers.",
                        verbose_name="Credits per Phone Derivation",
                    ),
                ),
                (
                    "stripe_plans",
                    models.ManyToManyField(
                        limit_choices_to={"active": True}, to="djstripe.Plan"
                    ),
                ),
            ],
            options={
                "verbose_name": "credit plan factory",
                "verbose_name_plural": "credit plan factories",
            },
        ),
    ]
