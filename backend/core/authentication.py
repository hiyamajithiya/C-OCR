"""
DRF Authentication classes — replaces FastAPI's Depends(get_current_user) and Depends(verify_api_key_header).
"""

from datetime import datetime
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from core.security import decode_access_token, hash_api_key
from accounts.models import User, Tenant
from api_keys.models import APIKey


class JWTBearerAuthentication(BaseAuthentication):
    """Authenticate via Authorization: Bearer <jwt>."""

    def authenticate(self, request):
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header.startswith("Bearer "):
            return None

        token = auth_header[7:]
        payload = decode_access_token(token)
        if payload is None:
            raise AuthenticationFailed("Invalid authentication credentials")

        user_id_str = payload.get("sub")
        if user_id_str is None:
            raise AuthenticationFailed("Invalid authentication credentials")

        try:
            user_id = int(user_id_str)
        except (ValueError, TypeError):
            raise AuthenticationFailed("Invalid authentication credentials")

        try:
            user = User.objects.select_related("tenant").get(id=user_id)
        except User.DoesNotExist:
            raise AuthenticationFailed("User not found")

        if not user.is_active:
            raise AuthenticationFailed("Inactive user")

        return (user, token)

    def authenticate_header(self, request):
        return "Bearer"


class APIKeyAuthentication(BaseAuthentication):
    """Authenticate via X-API-Key header with rate limiting."""

    def authenticate(self, request):
        api_key_value = request.META.get("HTTP_X_API_KEY", "")
        if not api_key_value:
            return None

        from services.api_key_service import rate_limiter

        # O(1) lookup by hashing the key and querying directly
        key_hash = hash_api_key(api_key_value)
        try:
            matched_key = APIKey.objects.get(key_hash=key_hash, is_active=True)
        except APIKey.DoesNotExist:
            raise AuthenticationFailed("Invalid API key")

        if matched_key.expires_at and matched_key.expires_at < datetime.utcnow():
            raise AuthenticationFailed("API key has expired")

        # Rate limit check
        is_allowed, current_count = rate_limiter.check_rate_limit(
            matched_key.id, matched_key.rate_limit
        )
        if not is_allowed:
            from rest_framework.exceptions import Throttled
            raise Throttled(
                wait=60,
                detail=f"Rate limit exceeded. Limit: {matched_key.rate_limit}/min, Current: {current_count}",
            )

        # Daily quota check
        quota_allowed, daily_count = rate_limiter.check_daily_quota(
            matched_key.id, matched_key.daily_quota
        )
        if not quota_allowed:
            from rest_framework.exceptions import Throttled
            raise Throttled(
                wait=86400,
                detail=f"Daily quota exceeded. Limit: {matched_key.daily_quota}/day, Used: {daily_count}",
            )

        # Update last used
        matched_key.last_used_at = datetime.utcnow()
        APIKey.objects.filter(id=matched_key.id).update(last_used_at=datetime.utcnow())

        # Get tenant
        try:
            tenant = Tenant.objects.get(id=matched_key.tenant_id)
        except Tenant.DoesNotExist:
            raise AuthenticationFailed("Tenant not found")

        if tenant.status != "active":
            raise AuthenticationFailed("Tenant is not active")

        # Store tenant on the request for views to access
        request.api_key = matched_key
        request.tenant = tenant

        return (matched_key, tenant)

    def authenticate_header(self, request):
        return "API-Key"
