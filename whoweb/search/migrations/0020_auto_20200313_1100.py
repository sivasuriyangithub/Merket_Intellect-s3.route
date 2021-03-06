# Generated by Django 2.2.8 on 2020-03-13 18:00

from django.db import migrations


def convert_seat_to_billing(apps, schema_editor):
    SearchExport = apps.get_model("search", "searchexport")
    for export in SearchExport.objects.filter(seat__isnull=False):
        export.billing_seat = export.seat.billing
        export.save(update_fields=["billing_seat"])


def convert_billing_to_seat(apps, schema_editor):
    SearchExport = apps.get_model("search", "searchexport")
    for export in SearchExport.objects.filter(billing_seat__isnull=False):
        export.seat = export.billing_seat.seat
        export.save(update_fields=["seat"])


class Migration(migrations.Migration):

    dependencies = [
        ("search", "0019_searchexport_billing_seat"),
    ]

    operations = [
        migrations.RunPython(
            convert_seat_to_billing, reverse_code=convert_billing_to_seat
        ),
    ]
