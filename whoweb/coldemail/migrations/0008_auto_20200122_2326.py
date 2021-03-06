# Generated by Django 2.2.8 on 2020-01-22 23:26

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        ("coldemail", "0007_auto_20200121_0120"),
    ]

    operations = [
        migrations.RemoveField(model_name="replyto", name="mailgun_route_id",),
        migrations.AddField(
            model_name="replyto",
            name="content_type",
            field=models.ForeignKey(
                default=0,
                on_delete=django.db.models.deletion.CASCADE,
                to="contenttypes.ContentType",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="replyto",
            name="object_id",
            field=models.PositiveIntegerField(default=0),
            preserve_default=False,
        ),
    ]
