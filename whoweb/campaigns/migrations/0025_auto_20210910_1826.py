# Generated by Django 2.2.19 on 2021-09-11 01:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("campaigns", "0024_auto_20210909_1136"),
    ]

    operations = [
        migrations.AlterField(
            model_name="icebreakertemplate",
            name="text",
            field=models.TextField(
                default="",
                help_text='<a href="https://jinja.palletsprojects.com/en/3.0.x/templates/" target=_blank>Documentation</a>',
            ),
        ),
    ]