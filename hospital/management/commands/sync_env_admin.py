from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create or sync the custom admin login from ADMIN_USERNAME and ADMIN_PASSWORD in .env."

    def handle(self, *args, **options):
        username = getattr(settings, "ADMIN_USERNAME", "").strip()
        password = getattr(settings, "ADMIN_PASSWORD", "")
        email = getattr(settings, "ADMIN_EMAIL", "admin@localhost").strip()
        if not username or not password:
            raise CommandError("Set ADMIN_USERNAME and ADMIN_PASSWORD in .env first.")
        if len(password) < 16:
            raise CommandError("ADMIN_PASSWORD must be at least 16 characters long.")

        User = get_user_model()
        user = User.objects.filter(username=username).first()
        if user is None:
            user = User.objects.create_superuser(username=username, email=email, password=password)
            action = "Created"
        else:
            user.email = email
            user.is_active = True
            user.is_staff = True
            user.is_superuser = True
            user.set_password(password)
            user.save(update_fields=["email", "is_active", "is_staff", "is_superuser", "password"])
            action = "Updated"

        self.stdout.write(self.style.SUCCESS(f"{action} custom admin account '{username}'."))
