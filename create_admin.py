"""
Quick script to create admin user in the database.
"""
import sys
import os

sys.path.insert(0, "backend")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cocr.settings")

import django
django.setup()

from accounts.models import Tenant, User
from core.security import get_password_hash
from datetime import datetime

try:
    tenant, created = Tenant.objects.get_or_create(
        name="Default Tenant", defaults={"status": "active"}
    )
    if created:
        print(f"Tenant created: {tenant.name} (ID: {tenant.id})")
    else:
        print(f"Using existing tenant: {tenant.name} (ID: {tenant.id})")

    users = [
        ("Admin User", "admin@c-ocr.local", "admin123", "admin"),
        ("Operator User", "operator@c-ocr.local", "operator123", "operator"),
        ("Reviewer User", "reviewer@c-ocr.local", "reviewer123", "reviewer"),
    ]

    for name, email, pwd, role in users:
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "tenant": tenant,
                "name": name,
                "password_hash": get_password_hash(pwd),
                "role": role,
                "is_active": True,
            },
        )
        if created:
            print(f"  Created {role}: {email} / {pwd}")
        else:
            print(f"  {role} already exists: {email}")

    print("\nDatabase setup complete!")

except Exception as e:
    print(f"Error: {e}")
