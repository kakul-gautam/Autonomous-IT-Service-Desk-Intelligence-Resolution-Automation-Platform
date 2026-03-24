from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    ROLE_ADMIN = 'ADMIN'
    ROLE_USER = 'USER'

    ROLE_CHOICES = [
        (ROLE_ADMIN, 'Admin'),
        (ROLE_USER, 'User'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ROLE_USER)
    department = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def get_display_role(self):
        return self.get_role_display()

    def __str__(self):
        return f"{self.user.username} - {self.get_display_role()}"
