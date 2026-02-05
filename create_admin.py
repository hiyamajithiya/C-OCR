"""
Quick script to create admin user in the database.
"""
import sys
sys.path.insert(0, 'backend')

from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from datetime import datetime

db = SessionLocal()

try:
    # Check if tenant exists
    tenant = db.query(Tenant).first()
    if not tenant:
        print("Creating default tenant...")
        tenant = Tenant(
            name="Default Tenant",
            status="active",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(tenant)
        db.commit()
        db.refresh(tenant)
        print(f"✓ Tenant created: {tenant.name} (ID: {tenant.id})")
    else:
        print(f"Using existing tenant: {tenant.name} (ID: {tenant.id})")

    # Check if admin user exists
    admin = db.query(User).filter(User.email == "admin@c-ocr.local").first()
    if admin:
        print("Admin user already exists!")
    else:
        print("Creating admin user...")
        admin = User(
            tenant_id=tenant.id,
            name="Admin User",
            email="admin@c-ocr.local",
            password_hash=get_password_hash("admin123"),
            role=UserRole.ADMIN,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        print(f"✓ Admin user created!")
        print(f"  Email: {admin.email}")
        print(f"  Password: admin123")
        print(f"  Role: {admin.role.value}")

    # Create operator user
    operator = db.query(User).filter(User.email == "operator@c-ocr.local").first()
    if not operator:
        print("\nCreating operator user...")
        operator = User(
            tenant_id=tenant.id,
            name="Operator User",
            email="operator@c-ocr.local",
            password_hash=get_password_hash("operator123"),
            role=UserRole.OPERATOR,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(operator)
        db.commit()
        print(f"✓ Operator user created!")
        print(f"  Email: {operator.email}")
        print(f"  Password: operator123")

    print("\n" + "="*60)
    print("Database setup complete!")
    print("="*60)

except Exception as e:
    print(f"Error: {e}")
    db.rollback()
finally:
    db.close()
