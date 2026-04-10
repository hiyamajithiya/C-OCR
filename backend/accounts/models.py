"""
Tenant and User models.
"""

from datetime import datetime
from django.db import models


class Tenant(models.Model):
    name = models.CharField(max_length=255, unique=True)
    status = models.CharField(max_length=50, default="active")
    created_at = models.DateTimeField(default=datetime.utcnow)
    updated_at = models.DateTimeField(default=datetime.utcnow)

    class Meta:
        db_table = "tenants"

    def save(self, *args, **kwargs):
        self.updated_at = datetime.utcnow()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Tenant({self.id}, {self.name})"


USER_ROLE_CHOICES = [
    ("admin", "Admin"),
    ("operator", "Operator"),
    ("reviewer", "Reviewer"),
]


class User(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="users")
    name = models.CharField(max_length=255)
    email = models.CharField(max_length=255, unique=True)
    password_hash = models.CharField(max_length=255)
    role = models.CharField(max_length=20, choices=USER_ROLE_CHOICES, default="operator")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=datetime.utcnow)
    updated_at = models.DateTimeField(default=datetime.utcnow)
    last_login_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "users"

    def save(self, *args, **kwargs):
        self.updated_at = datetime.utcnow()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"User({self.id}, {self.email})"
