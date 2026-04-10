"""
DRF Permission classes — replaces FastAPI's get_current_admin_user, get_current_reviewer_user.
"""

from rest_framework.permissions import BasePermission


class IsActiveUser(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if user is None:
            return False
        # For API key auth, request.user is the APIKey object
        if hasattr(user, "is_active"):
            return user.is_active
        return True


class IsAdminUser(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return user is not None and hasattr(user, "role") and user.role == "admin"


class IsReviewerOrAdmin(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return user is not None and hasattr(user, "role") and user.role in ("admin", "reviewer")


class AllowAny(BasePermission):
    def has_permission(self, request, view):
        return True


class IsAPIKeyAuthenticated(BasePermission):
    """For external API endpoints that require API key auth."""
    def has_permission(self, request, view):
        return hasattr(request, "api_key") and request.api_key is not None
