"""
Main API router combining all endpoint routers.
"""

from fastapi import APIRouter

from app.api.endpoints import (
    auth,
    documents,
    templates,
    api_keys,
    users,
    audit_logs,
    corrections,
    external_api,
)

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(documents.router, prefix="/documents", tags=["Documents"])
api_router.include_router(templates.router, prefix="/templates", tags=["Templates"])
api_router.include_router(api_keys.router, prefix="/api-keys", tags=["API Keys"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(audit_logs.router, prefix="/audit-logs", tags=["Audit Logs"])
api_router.include_router(corrections.router, prefix="/corrections", tags=["Corrections"])
api_router.include_router(external_api.router, prefix="/external", tags=["External API"])
