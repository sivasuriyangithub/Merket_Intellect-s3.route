# Generated by Django 2.2.6 on 2019-11-14 02:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("search", "0001_squashed_0005_auto_20191106_0001")]

    operations = [
        migrations.AlterField(
            model_name="searchexport",
            name="status",
            field=models.IntegerField(
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
                max_length=100,
                verbose_name="status",
            ),
        ),
        migrations.AlterField(
            model_name="searchexport",
            name="valid_count",
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
