from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from accounts.models import Account
from hospital.models import DEPARTMENT_CHOICES, Doctor


class Command(BaseCommand):
    help = "Add a demo doctor for each department that has no doctor yet."

    def handle(self, *args, **options):
        created = 0
        for department, label in DEPARTMENT_CHOICES:
            # Mark profiles created by the original demo command as sample data too.
            demo_username = f"demo_{slugify(department).replace('-', '_')}"
            demo_doctor = Doctor.objects.filter(user__username=demo_username).first()
            if demo_doctor and not demo_doctor.is_sample:
                demo_doctor.is_sample = True
                demo_doctor.save(update_fields=["is_sample"])
            if Doctor.objects.filter(department=department).exists():
                continue

            key = slugify(department).replace("-", "_")
            username = f"demo_{key}"
            user, user_created = User.objects.get_or_create(
                username=username,
                defaults={
                    "first_name": "Aarav",
                    "last_name": f"{department.replace(' ', '')}Doctor",
                    "email": f"{username}@example.com",
                },
            )
            if user_created:
                user.set_unusable_password()
                user.save(update_fields=["password"])
            Account.objects.get_or_create(
                user=user,
                defaults={"phone": "0000000000", "role": "doctor"},
            )
            Doctor.objects.create(
                user=user,
                specialization=label,
                department=department,
                experience=5,
                language="English, Hindi",
                location="Main Hospital",
            )
            created += 1
            self.stdout.write(f"Added {user.get_full_name()} — {department}")

        self.stdout.write(self.style.SUCCESS(f"Done. Added {created} demo doctor(s)."))
