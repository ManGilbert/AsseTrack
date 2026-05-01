from django.db import migrations, models


def migrate_device_status(apps, schema_editor):
    Device = apps.get_model("App", "Device")
    DeviceAssignment = apps.get_model("App", "DeviceAssignment")

    for device in Device.objects.all():
        active_assignment_exists = DeviceAssignment.objects.filter(device=device, returned_at__isnull=True).exists()
        device.status = "not_available" if active_assignment_exists else "available"
        device.save(update_fields=["status"])


class Migration(migrations.Migration):

    dependencies = [
        ("App", "0004_remove_deviceassignment_unique_active_device_assignment_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="device",
            name="status",
            field=models.CharField(
                choices=[
                    ("available", "Available"),
                    ("not_available", "Not Available"),
                ],
                default="available",
                max_length=20,
            ),
            preserve_default=False,
        ),
        migrations.RunPython(migrate_device_status, migrations.RunPython.noop),
    ]
