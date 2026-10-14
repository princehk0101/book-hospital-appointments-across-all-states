import uuid

import django.utils.timezone
from django.db import migrations, models


def assign_booking_references(apps, schema_editor):
    Appointment = apps.get_model("hospital", "Appointment")
    for appointment in Appointment.objects.filter(booking_reference__isnull=True).only("pk").iterator():
        Appointment.objects.filter(pk=appointment.pk).update(booking_reference=uuid.uuid4())


class Migration(migrations.Migration):

    dependencies = [
        ("hospital", "0005_doctor_profile_photo"),
    ]

    operations = [
        migrations.AddField(
            model_name="appointment",
            name="booking_reference",
            field=models.UUIDField(blank=True, editable=False, null=True, unique=True),
        ),
        migrations.RunPython(assign_booking_references, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="appointment",
            name="booking_reference",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
        migrations.AddField(
            model_name="appointment",
            name="payment_status",
            field=models.CharField(
                choices=[("Pending", "Pending"), ("Paid", "Paid"), ("Failed", "Failed")],
                default="Paid",
                max_length=12,
            ),
        ),
        migrations.AlterField(
            model_name="appointment",
            name="payment_status",
            field=models.CharField(
                choices=[("Pending", "Pending"), ("Paid", "Paid"), ("Failed", "Failed")],
                default="Pending",
                max_length=12,
            ),
        ),
        migrations.AddField(
            model_name="appointment",
            name="payment_amount",
            field=models.DecimalField(decimal_places=2, default=50.0, max_digits=7),
        ),
        migrations.AddField(
            model_name="appointment",
            name="razorpay_order_id",
            field=models.CharField(blank=True, max_length=80, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="appointment",
            name="razorpay_payment_id",
            field=models.CharField(blank=True, max_length=80, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="appointment",
            name="created_at",
            field=models.DateTimeField(default=django.utils.timezone.now, editable=False),
        ),
        migrations.AlterField(
            model_name="appointment",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name="appointment",
            name="status",
            field=models.CharField(
                choices=[
                    ("Pending Payment", "Pending Payment"),
                    ("Waiting", "Waiting"),
                    ("In Process", "In Process"),
                    ("Completed", "Completed"),
                    ("Cancelled", "Cancelled"),
                ],
                default="Waiting",
                max_length=20,
            ),
        ),
    ]
