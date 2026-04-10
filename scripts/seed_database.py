"""
Database seed script to create initial tenant, users, and API key.
Run this script after database migrations to set up the initial data.
"""

import sys
import os
from pathlib import Path

backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cocr.settings")

import django
django.setup()

from accounts.models import Tenant, User
from core.security import get_password_hash, generate_api_key, hash_api_key, get_api_key_prefix
from api_keys.models import APIKey

print("Seeding database...")

# Create tenant
tenant, created = Tenant.objects.get_or_create(
    name="Default Tenant", defaults={"status": "active"}
)
print(f"{'Created' if created else 'Existing'} tenant: {tenant.name} (ID: {tenant.id})")

# Create users
users_data = [
    ("Admin User", "admin@c-ocr.local", "admin123", "admin"),
    ("Operator User", "operator@c-ocr.local", "operator123", "operator"),
    ("Reviewer User", "reviewer@c-ocr.local", "reviewer123", "reviewer"),
]

for name, email, pwd, role in users_data:
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
    status = "Created" if created else "Existing"
    print(f"  {status} {role}: {email} / {pwd}")

# Create default API key
if not APIKey.objects.filter(tenant=tenant).exists():
    raw_key = generate_api_key()
    api_key = APIKey.objects.create(
        tenant=tenant,
        key_hash=hash_api_key(raw_key),
        key_prefix=get_api_key_prefix(raw_key),
        name="Default API Key",
        scopes=["documents:read", "documents:write", "templates:read"],
        rate_limit=60,
        daily_quota=1000,
        is_active=True,
    )
    print(f"\n  Created API Key: {raw_key}")
    print(f"  (Save this key - it won't be shown again)")
else:
    print("\n  API key already exists")

print("\nDatabase seeding complete!")
