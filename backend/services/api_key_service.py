"""
API Key service for rate limiting, usage tracking, and statistics.
"""

import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple

import redis
from django.conf import settings
from django.db.models import Avg, Count, Max, Q, F

from api_keys.models import APIKey, APIKeyUsage, APIKeyDailyStats, APIKeyTemplate
from templates_app.models import Template


_redis = redis.Redis.from_url(settings.REDIS_URL)


class RateLimiter:
    """
    Redis-backed rate limiter for API keys.
    Uses sorted sets for sliding-window minute tracking and simple counters for daily quotas.
    """

    def check_rate_limit(self, api_key_id: int, rate_limit: int) -> Tuple[bool, int]:
        """
        Check if the API key has exceeded its per-minute rate limit.

        Uses a Redis sorted set as a sliding window (last 60 seconds).

        Returns:
            Tuple of (is_allowed, current_count)
        """
        key = f"ratelimit:minute:{api_key_id}"
        now = time.time()
        window_start = now - 60

        pipe = _redis.pipeline()
        pipe.zremrangebyscore(key, "-inf", window_start)
        pipe.zcard(key)
        pipe.execute()

        current_count = _redis.zcard(key)
        return current_count < rate_limit, current_count

    def record_request(self, api_key_id: int):
        """Record a new request in the per-minute sliding window."""
        key = f"ratelimit:minute:{api_key_id}"
        now = time.time()
        member = f"{now}"

        pipe = _redis.pipeline()
        pipe.zadd(key, {member: now})
        pipe.expire(key, 120)  # TTL slightly longer than window
        pipe.execute()

    def check_daily_quota(self, api_key_id: int, daily_quota: int) -> Tuple[bool, int]:
        """
        Check if the API key has exceeded its daily quota.

        Uses a Redis key with date suffix and INCR pattern.

        Returns:
            Tuple of (is_allowed, current_count)
        """
        today = datetime.utcnow().strftime("%Y-%m-%d")
        key = f"ratelimit:daily:{api_key_id}:{today}"

        current_count = _redis.get(key)
        current_count = int(current_count) if current_count else 0
        return current_count < daily_quota, current_count

    def record_daily_request(self, api_key_id: int):
        """Increment the daily request counter."""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        key = f"ratelimit:daily:{api_key_id}:{today}"

        pipe = _redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, 86400)
        pipe.execute()

    def get_current_minute_usage(self, api_key_id: int) -> int:
        """Get the current minute's request count from the sliding window."""
        key = f"ratelimit:minute:{api_key_id}"
        now = time.time()
        window_start = now - 60

        pipe = _redis.pipeline()
        pipe.zremrangebyscore(key, "-inf", window_start)
        pipe.zcard(key)
        results = pipe.execute()

        return results[1]

    def get_daily_usage(self, api_key_id: int) -> int:
        """Get today's request count."""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        key = f"ratelimit:daily:{api_key_id}:{today}"

        count = _redis.get(key)
        return int(count) if count else 0


# Global rate limiter instance
rate_limiter = RateLimiter()


class APIKeyService:
    """Service for API key operations, usage tracking, and statistics."""

    def check_template_access(self, api_key: APIKey, template_id: int) -> bool:
        """
        Check if the API key has access to the specified template.

        Args:
            api_key: The API key to check
            template_id: The template ID to access

        Returns:
            True if access is allowed, False otherwise
        """
        # If not restricted to templates, allow all
        if not api_key.restrict_to_templates:
            return True

        # Check if template exists for this tenant
        template = Template.objects.filter(
            id=template_id, tenant_id=api_key.tenant_id
        ).first()

        if not template:
            return False

        # Check if template is in the allowed templates
        return api_key.allowed_templates.filter(id=template_id).exists()

    def get_allowed_templates(self, api_key: APIKey) -> List[Template]:
        """Get list of templates the API key can access."""
        if not api_key.restrict_to_templates:
            # Return all templates for the tenant
            return list(
                Template.objects.filter(
                    tenant_id=api_key.tenant_id, is_active=True
                )
            )

        return list(api_key.allowed_templates.all())

    def record_usage(
        self,
        api_key: APIKey,
        endpoint: str,
        method: str,
        status_code: Optional[int] = None,
        template_id: Optional[int] = None,
        document_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        response_time_ms: Optional[int] = None,
    ) -> APIKeyUsage:
        """
        Record an API key usage event.
        """
        usage = APIKeyUsage(
            api_key_id=api_key.id,
            tenant_id=api_key.tenant_id,
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            template_id=template_id,
            document_id=document_id,
            ip_address=ip_address,
            user_agent=user_agent,
            response_time_ms=response_time_ms,
        )
        usage.save()

        # Update Redis rate limiter
        rate_limiter.record_request(api_key.id)
        rate_limiter.record_daily_request(api_key.id)

        return usage

    def update_daily_stats(self, api_key: APIKey):
        """
        Update or create daily statistics for the API key.
        Called periodically or after recording usage.
        """
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today + timedelta(days=1)

        # Get or create daily stats
        daily_stat, created = APIKeyDailyStats.objects.get_or_create(
            api_key_id=api_key.id,
            date=today,
            defaults={
                "tenant_id": api_key.tenant_id,
                "quota_limit": api_key.daily_quota,
            },
        )

        # Aggregate today's usage
        usage_qs = APIKeyUsage.objects.filter(
            api_key_id=api_key.id,
            created_at__gte=today,
            created_at__lt=today_end,
        )

        total_requests = usage_qs.count()
        successful = usage_qs.filter(
            status_code__gte=200, status_code__lt=300
        ).count()
        failed = usage_qs.filter(status_code__gte=400).count()

        # Count endpoint types
        documents_accessed = usage_qs.filter(
            endpoint__contains="/documents"
        ).count()
        templates_accessed = usage_qs.filter(
            endpoint__contains="/templates"
        ).count()
        extractions = usage_qs.filter(
            endpoint__contains="/extract"
        ).count()

        # Response time stats
        time_stats = usage_qs.filter(
            response_time_ms__isnull=False,
            created_at__gte=today,
            created_at__lt=today_end,
        ).aggregate(
            avg_time=Avg("response_time_ms"),
            max_time=Max("response_time_ms"),
        )

        avg_time = time_stats["avg_time"]
        max_time = time_stats["max_time"]

        # Update stats
        daily_stat.total_requests = total_requests
        daily_stat.successful_requests = successful
        daily_stat.failed_requests = failed
        daily_stat.documents_accessed = documents_accessed
        daily_stat.templates_accessed = templates_accessed
        daily_stat.extractions_performed = extractions
        daily_stat.avg_response_time_ms = int(avg_time) if avg_time else None
        daily_stat.max_response_time_ms = max_time
        daily_stat.quota_used = total_requests
        daily_stat.save()

        return daily_stat

    def get_usage_stats(self, api_key_id: int, days: int = 30) -> Dict[str, Any]:
        """
        Get comprehensive usage statistics for an API key.
        """
        api_key = APIKey.objects.filter(id=api_key_id).first()
        if not api_key:
            return {}

        start_date = datetime.utcnow() - timedelta(days=days)

        # Get usage records
        usage_qs = APIKeyUsage.objects.filter(
            api_key_id=api_key_id, created_at__gte=start_date
        )

        total_requests = usage_qs.count()

        # Status breakdown
        successful = usage_qs.filter(
            status_code__gte=200, status_code__lt=300
        ).count()
        client_errors = usage_qs.filter(
            status_code__gte=400, status_code__lt=500
        ).count()
        server_errors = usage_qs.filter(status_code__gte=500).count()

        # Daily breakdown
        daily_stats = list(
            APIKeyDailyStats.objects.filter(
                api_key_id=api_key_id,
                date__gte=start_date,
            ).order_by("date")
        )

        # Today's stats
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_usage = APIKeyUsage.objects.filter(
            api_key_id=api_key_id, created_at__gte=today
        ).count()

        # Current rate usage (from Redis)
        current_minute_usage = rate_limiter.get_current_minute_usage(api_key_id)

        # Top endpoints
        top_endpoints = list(
            usage_qs.values("endpoint")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )

        return {
            "api_key_id": api_key_id,
            "api_key_name": api_key.name,
            "period_days": days,
            "total_requests": total_requests,
            "successful_requests": successful,
            "client_errors": client_errors,
            "server_errors": server_errors,
            "success_rate": (
                round(successful / total_requests * 100, 2) if total_requests > 0 else 0
            ),
            "today": {
                "requests": today_usage,
                "quota_limit": api_key.daily_quota,
                "quota_remaining": max(0, api_key.daily_quota - today_usage),
                "quota_percent_used": (
                    round(today_usage / api_key.daily_quota * 100, 2)
                    if api_key.daily_quota > 0
                    else 0
                ),
            },
            "rate_limit": {
                "limit_per_minute": api_key.rate_limit,
                "current_minute_usage": current_minute_usage,
                "remaining": max(0, api_key.rate_limit - current_minute_usage),
            },
            "daily_breakdown": [
                {
                    "date": stat.date.strftime("%Y-%m-%d"),
                    "total": stat.total_requests,
                    "successful": stat.successful_requests,
                    "failed": stat.failed_requests,
                }
                for stat in daily_stats
            ],
            "top_endpoints": [
                {"endpoint": ep["endpoint"], "count": ep["count"]}
                for ep in top_endpoints
            ],
        }

    def get_all_keys_stats(self, tenant_id: int) -> List[Dict[str, Any]]:
        """Get summary statistics for all API keys in a tenant."""
        api_keys = APIKey.objects.filter(tenant_id=tenant_id)

        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        results = []

        for key in api_keys:
            # Today's usage
            today_usage = APIKeyUsage.objects.filter(
                api_key_id=key.id, created_at__gte=today
            ).count()

            # Total usage (all time)
            total_usage = APIKeyUsage.objects.filter(
                api_key_id=key.id
            ).count()

            # Last 7 days
            week_ago = today - timedelta(days=7)
            week_usage = APIKeyUsage.objects.filter(
                api_key_id=key.id, created_at__gte=week_ago
            ).count()

            results.append(
                {
                    "id": key.id,
                    "name": key.name,
                    "key_prefix": key.key_prefix,
                    "is_active": key.is_active,
                    "rate_limit": key.rate_limit,
                    "daily_quota": key.daily_quota,
                    "restrict_to_templates": key.restrict_to_templates,
                    "allowed_template_count": (
                        key.allowed_templates.count()
                        if key.restrict_to_templates
                        else None
                    ),
                    "created_at": key.created_at.isoformat(),
                    "last_used_at": (
                        key.last_used_at.isoformat() if key.last_used_at else None
                    ),
                    "usage": {
                        "today": today_usage,
                        "today_quota_percent": (
                            round(today_usage / key.daily_quota * 100, 2)
                            if key.daily_quota > 0
                            else 0
                        ),
                        "week": week_usage,
                        "total": total_usage,
                        "current_minute": rate_limiter.get_current_minute_usage(key.id),
                    },
                }
            )

        return results
