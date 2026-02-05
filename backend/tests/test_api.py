"""
Basic API acceptance tests for C-OCR platform.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import Base, get_db
from app.core.security import get_password_hash
from app.models.tenant import Tenant
from app.models.user import User, UserRole

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="module")
def test_db():
    """Create test database and tables."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Get database session for testing."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    # Override dependency
    def override_get_db():
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(test_db, db_session):
    """Get test client."""
    return TestClient(app)


@pytest.fixture(scope="function")
def test_tenant(db_session):
    """Create test tenant."""
    tenant = Tenant(name="Test Tenant", status="active")
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)
    return tenant


@pytest.fixture(scope="function")
def test_admin_user(db_session, test_tenant):
    """Create test admin user."""
    user = User(
        tenant_id=test_tenant.id,
        name="Test Admin",
        email="test@example.com",
        password_hash=get_password_hash("testpass123"),
        role=UserRole.ADMIN,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def auth_headers(client, test_admin_user):
    """Get authentication headers."""
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "test@example.com", "password": "testpass123"}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestHealthCheck:
    """Test health check endpoint."""

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestAuthentication:
    """Test authentication endpoints."""

    def test_login_success(self, client, test_admin_user):
        """Test successful login."""
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "test@example.com", "password": "testpass123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "test@example.com"

    def test_login_invalid_credentials(self, client, test_admin_user):
        """Test login with invalid credentials."""
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "test@example.com", "password": "wrongpassword"}
        )
        assert response.status_code == 401


class TestUsers:
    """Test user management endpoints."""

    def test_get_current_user(self, client, auth_headers, test_admin_user):
        """Test getting current user information."""
        response = client.get("/api/v1/users/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["role"] == "admin"

    def test_list_users(self, client, auth_headers, test_admin_user):
        """Test listing users."""
        response = client.get("/api/v1/users/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_create_user(self, client, auth_headers, test_admin_user):
        """Test creating a new user."""
        response = client.post(
            "/api/v1/users/",
            headers=auth_headers,
            json={
                "name": "New User",
                "email": "newuser@example.com",
                "password": "password123",
                "role": "operator"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["role"] == "operator"


class TestAPIKeys:
    """Test API key management endpoints."""

    def test_create_api_key(self, client, auth_headers, test_admin_user):
        """Test creating an API key."""
        response = client.post(
            "/api/v1/api-keys/",
            headers=auth_headers,
            json={
                "name": "Test API Key",
                "scopes": ["documents:read", "documents:write"],
                "rate_limit": 100,
                "daily_quota": 5000
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test API Key"
        assert "raw_key" in data  # Only shown on creation

    def test_list_api_keys(self, client, auth_headers, test_admin_user):
        """Test listing API keys."""
        response = client.get("/api/v1/api-keys/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestTemplates:
    """Test template management endpoints."""

    def test_create_template(self, client, auth_headers, test_admin_user):
        """Test creating a template."""
        response = client.post(
            "/api/v1/templates/",
            headers=auth_headers,
            json={
                "name": "Test Invoice Template",
                "description": "Template for testing",
                "doc_category": "invoice"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Invoice Template"
        assert data["doc_category"] == "invoice"

    def test_list_templates(self, client, auth_headers, test_admin_user):
        """Test listing templates."""
        response = client.get("/api/v1/templates/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestDocuments:
    """Test document processing endpoints."""

    def test_upload_document_no_file(self, client, auth_headers):
        """Test document upload without file."""
        response = client.post("/api/v1/documents/", headers=auth_headers)
        assert response.status_code == 422  # Validation error


class TestAuditLogs:
    """Test audit log endpoints."""

    def test_list_audit_logs(self, client, auth_headers, test_admin_user):
        """Test listing audit logs."""
        response = client.get("/api/v1/audit-logs/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
