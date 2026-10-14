from django.db import migrations, models


def mark_pre_payment_bookings_as_legacy(apps, schema_editor):
    Appointment = apps.get_model("hospital", "Appointment")
    Appointment.objects.filter(
        razorpay_order_id__isnull=True,
        payment_status="Paid",
    ).update(payment_status="Legacy", payment_amount=0)


class Migration(migrations.Migration):

    dependencies = [
        ("hospital", "0006_appointment_payment_details"),
    ]

    operations = [
        migrations.RunPython(mark_pre_payment_bookings_as_legacy, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="appointment",
            name="payment_status",
            field=models.CharField(
                choices=[
                    ("Pending", "Pending"),
                    ("Paid", "Paid"),
                    ("Failed", "Failed"),
                    ("Legacy", "No payment required"),
                ],
                default="Pending",
                max_length=12,
            ),
        ),
    ]
