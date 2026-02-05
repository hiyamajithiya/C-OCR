"""
Database seed script to create initial tenant, admin user, and API key.
Run this script after database migrations to set up the initial data.
"""

import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine, Base
from app.core.security import get_password_hash, generate_api_key, hash_api_key, get_api_key_prefix
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.models.api_key import APIKey
from datetime import datetime


def seed_database():
    """
    Seed the database with initial data.
    """
    # Create tables
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✓ Database tables created")

    # Create database session
    db: Session = SessionLocal()

    try:
        # Check if tenant already exists
        existing_tenant = db.query(Tenant).first()
        if existing_tenant:
            print("⚠ Database already seeded. Skipping...")
            return

        # Create default tenant
        print("\nCreating default tenant...")
        tenant = Tenant(
            name="Default Tenant",
            status="active"
        )
        db.add(tenant)
        db.commit()
        db.refresh(tenant)
        print(f"✓ Tenant created: {tenant.name} (ID: {tenant.id})")

        # Create admin user
        print("\nCreating admin user...")
        admin_password = "admin123"  # Change this in production!
        admin_user = User(
            tenant_id=tenant.id,
            name="Admin User",
            email="admin@c-ocr.local",
            password_hash=get_password_hash(admin_password),
            role=UserRole.ADMIN,
            is_active=True
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        print(f"✓ Admin user created:")
        print(f"  Email: {admin_user.email}")
        print(f"  Password: {admin_password}")
        print(f"  Role: {admin_user.role.value}")

        # Create API key
        print("\nCreating default API key...")
        raw_key = generate_api_key()
        key_hash = hash_api_key(raw_key)
        key_prefix = get_api_key_prefix(raw_key)

        api_key = APIKey(
            tenant_id=tenant.id,
            key_hash=key_hash,
            key_prefix=key_prefix,
            name="Default API Key",
            scopes=["documents:read", "documents:write", "templates:read", "templates:write"],
            rate_limit=100,
            daily_quota=5000,
            is_active=True
        )
        db.add(api_key)
        db.commit()
        db.refresh(api_key)
        print(f"✓ API Key created:")
        print(f"  Name: {api_key.name}")
        print(f"  Key: {raw_key}")
        print(f"  ⚠ IMPORTANT: Save this key! It will not be shown again.")

        # Create additional users (optional)
        print("\nCreating additional users...")

        # Operator user
        operator_user = User(
            tenant_id=tenant.id,
            name="Operator User",
            email="operator@c-ocr.local",
            password_hash=get_password_hash("operator123"),
            role=UserRole.OPERATOR,
            is_active=True
        )
        db.add(operator_user)

        # Reviewer user
        reviewer_user = User(
            tenant_id=tenant.id,
            name="Reviewer User",
            email="reviewer@c-ocr.local",
            password_hash=get_password_hash("reviewer123"),
            role=UserRole.REVIEWER,
            is_active=True
        )
        db.add(reviewer_user)

        db.commit()
        print(f"✓ Operator user created: operator@c-ocr.local / operator123")
        print(f"✓ Reviewer user created: reviewer@c-ocr.local / reviewer123")

        print("\n" + "="*60)
        print("DATABASE SEEDING COMPLETED SUCCESSFULLY!")
        print("="*60)
        print("\nDefault Credentials:")
        print(f"  Admin:    admin@c-ocr.local / {admin_password}")
        print(f"  Operator: operator@c-ocr.local / operator123")
        print(f"  Reviewer: reviewer@c-ocr.local / reviewer123")
        print(f"\nAPI Key: {raw_key}")
        print("\n⚠ IMPORTANT: Change all default passwords in production!")
        print("="*60)

    except Exception as e:
        print(f"\n✗ Error seeding database: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("="*60)
    print("C-OCR DATABASE SEED SCRIPT")
    print("="*60)
    seed_database()
