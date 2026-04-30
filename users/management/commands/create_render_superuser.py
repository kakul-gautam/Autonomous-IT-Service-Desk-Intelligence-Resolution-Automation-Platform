import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Create or promote a superuser from environment variables.'

    def handle(self, *args, **options):
        username = os.getenv('DJANGO_SUPERUSER_USERNAME', '').strip()
        email = os.getenv('DJANGO_SUPERUSER_EMAIL', '').strip()
        password = os.getenv('DJANGO_SUPERUSER_PASSWORD', '').strip()

        if not username or not password:
            self.stdout.write(self.style.WARNING('Superuser env vars not set; skipping superuser bootstrap.'))
            return

        User = get_user_model()
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': email,
                'is_staff': True,
                'is_superuser': True,
            },
        )

        if email and user.email != email:
            user.email = email

        if not user.is_staff:
            user.is_staff = True
        if not user.is_superuser:
            user.is_superuser = True

        user.set_password(password)
        user.save()

        try:
            from users.models import UserProfile

            profile, _ = UserProfile.objects.get_or_create(user=user)
            if profile.role != UserProfile.ROLE_ADMIN:
                profile.role = UserProfile.ROLE_ADMIN
                profile.save(update_fields=['role'])
        except Exception:
            pass

        if created:
            self.stdout.write(self.style.SUCCESS(f'Superuser {username!r} created.'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Superuser {username!r} updated.'))