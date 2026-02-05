"""
API Key service for rate limiting, usage tracking, and statistics.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from collections import defaultdict
import threading
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.models.api_key import APIKey
from app.models.api_key_usage import APIKeyUsage, APIKeyDailyStats
from app.models.template import Template


class RateLimiter:
    """
    In-memory rate limiter for API keys.
    Tracks requests per minute for each API key.
    """

    def __init__(self):
        self._requests: Dict[int, List[datetime]] = defaultdict(list)
        self._daily_counts: Dict[Tuple[int, str], int] = defaultdict(int)
        self._lock = threading.Lock()

    def _cleanup_old_requests(self, api_key_id: int, window_seconds: int = 60):
        """Remove requests older than the window."""
        cutoff = datetime.utcnow() - timedelta(seconds=window_seconds)
        self._requests[api_key_id] = [
            ts for ts in self._requests[api_key_id] if ts > cutoff
        ]

    def check_rate_limit(self, api_key_id: int, rate_limit: int) -> Tuple[bool, int]:
        """
        Check if the API key has exceeded its rate limit.

        Returns:
            Tuple of (is_allowed, current_count)
        """
        with self._lock:
            self._cleanup_old_requests(api_key_id)
            current_count = len(self._requests[api_key_id])
            return current_count < rate_limit, current_count

    def record_request(self, api_key_id: int):
        """Record a new request for the API key."""
        with self._lock:
            self._requests[api_key_id].append(datetime.utcnow())

    def check_daily_quota(self, api_key_id: int, daily_quota: int) -> Tuple[bool, int]:
        """
        Check if the API key has exceeded its daily quota.

        Returns:
            Tuple of (is_allowed, current_count)
        """
        today = datetime.utcnow().strftime("%Y-%m-%d")
        key = (api_key_id, today)

        with self._lock:
            current_count = self._daily_counts[key]
            return current_count < daily_quota, current_count

    def record_daily_request(self, api_key_id: int):
        """Record a request against the daily quota."""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        key = (api_key_id, today)

        with self._lock:
            self._daily_counts[key] += 1

    def get_current_minute_usage(self, api_key_id: int) -> int:
        """Get the current minute's request count."""
        with self._lock:
            self._cleanup_old_requests(api_key_id)
            return len(self._requests[api_key_id])

    def get_daily_usage(self, api_key_id: int) -> int:
        """Get today's request count."""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        key = (api_key_id, today)
        with self._lock:
            return self._daily_counts[key]


# Global rate limiter instance
rate_limiter = RateLimiter()


class APIKeyService:
    """Service for API key operations, usage tracking, and statistics."""

    def __init__(self, db: Session):
        self.db = db

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

        # Check if template is in allowed list
        template = self.db.query(Template).filter(
            Template.id == template_id,
            Template.tenant_id == api_key.tenant_id
        ).first()

        if not template:
            return False

        # Check if template is in the allowed templates
        return template in api_key.allowed_templates

    def get_allowed_templates(self, api_key: APIKey) -> List[Template]:
        """Get list of templates the API key can access."""
        if not api_key.restrict_to_templates:
            # Return all templates for the tenant
            return self.db.query(Template).filter(
                Template.tenant_id == api_key.tenant_id,
                Template.is_active == True
            ).all()

        return list(api_key.allowed_templates)

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
        response_time_ms: Optional[int] = None
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
            response_time_ms=response_time_ms
        )
        self.db.add(usage)
        self.db.commit()
        self.db.refresh(usage)

        # Update in-memory rate limiter
        rate_limiter.record_request(api_key.id)
        rate_limiter.record_daily_request(api_key.id)

        return usage

    def update_daily_stats(self, api_key: APIKey):
        """
        Update or create daily statistics for the API key.
        Called periodically or after recording usage.
        """
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        # Get or create daily stats
        daily_stat = self.db.query(APIKeyDailyStats).filter(
            APIKeyDailyStats.api_key_id == api_key.id,
            APIKeyDailyStats.date == today
        ).first()

        if not daily_stat:
            daily_stat = APIKeyDailyStats(
                api_key_id=api_key.id,
                tenant_id=api_key.tenant_id,
                date=today,
                quota_limit=api_key.daily_quota
            )
            self.db.add(daily_stat)

        # Aggregate today's usage
        today_end = today + timedelta(days=1)
        usage_query = self.db.query(APIKeyUsage).filter(
            APIKeyUsage.api_key_id == api_key.id,
            APIKeyUsage.created_at >= today,
            APIKeyUsage.created_at < today_end
        )

        total_requests = usage_query.count()
        successful = usage_query.filter(
            APIKeyUsage.status_code >= 200,
            APIKeyUsage.status_code < 300
        ).count()
        failed = usage_query.filter(
            APIKeyUsage.status_code >= 400
        ).count()

        # Count endpoint types
        documents_accessed = usage_query.filter(
            APIKeyUsage.endpoint.like('%/documents%')
        ).count()
        templates_accessed = usage_query.filter(
            APIKeyUsage.endpoint.like('%/templates%')
        ).count()
        extractions = usage_query.filter(
            APIKeyUsage.endpoint.like('%/extract%')
        ).count()

        # Response time stats
        avg_time = self.db.query(func.avg(APIKeyUsage.response_time_ms)).filter(
            APIKeyUsage.api_key_id == api_key.id,
            APIKeyUsage.created_at >= today,
            APIKeyUsage.created_at < today_end,
            APIKeyUsage.response_time_ms.isnot(None)
        ).scalar()

        max_time = self.db.query(func.max(APIKeyUsage.response_time_ms)).filter(
            APIKeyUsage.api_key_id == api_key.id,
            APIKeyUsage.created_at >= today,
            APIKeyUsage.created_at < today_end
        ).scalar()

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

        self.db.commit()
        return daily_stat

    def get_usage_stats(
        self,
        api_key_id: int,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get comprehensive usage statistics for an API key.
        """
        api_key = self.db.query(APIKey).filter(APIKey.id == api_key_id).first()
        if not api_key:
            return {}

        start_date = datetime.utcnow() - timedelta(days=days)

        # Get usage records
        usage_query = self.db.query(APIKeyUsage).filter(
            APIKeyUsage.api_key_id == api_key_id,
            APIKeyUsage.created_at >= start_date
        )

        total_requests = usage_query.count()

        # Status breakdown
        successful = usage_query.filter(
            APIKeyUsage.status_code >= 200,
            APIKeyUsage.status_code < 300
        ).count()
        client_errors = usage_query.filter(
            APIKeyUsage.status_code >= 400,
            APIKeyUsage.status_code < 500
        ).count()
        server_errors = usage_query.filter(
            APIKeyUsage.status_code >= 500
        ).count()

        # Daily breakdown
        daily_stats = self.db.query(APIKeyDailyStats).filter(
            APIKeyDailyStats.api_key_id == api_key_id,
            APIKeyDailyStats.date >= start_date
        ).order_by(APIKeyDailyStats.date).all()

        # Today's stats
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_usage = self.db.query(APIKeyUsage).filter(
            APIKeyUsage.api_key_id == api_key_id,
            APIKeyUsage.created_at >= today
        ).count()

        # Current rate usage (from in-memory)
        current_minute_usage = rate_limiter.get_current_minute_usage(api_key_id)

        # Top endpoints
        top_endpoints = self.db.query(
            APIKeyUsage.endpoint,
            func.count(APIKeyUsage.id).label('count')
        ).filter(
            APIKeyUsage.api_key_id == api_key_id,
            APIKeyUsage.created_at >= start_date
        ).group_by(APIKeyUsage.endpoint).order_by(
            func.count(APIKeyUsage.id).desc()
        ).limit(10).all()

        return {
            "api_key_id": api_key_id,
            "api_key_name": api_key.name,
            "period_days": days,
            "total_requests": total_requests,
            "successful_requests": successful,
            "client_errors": client_errors,
            "server_errors": server_errors,
            "success_rate": round(successful / total_requests * 100, 2) if total_requests > 0 else 0,
            "today": {
                "requests": today_usage,
                "quota_limit": api_key.daily_quota,
                "quota_remaining": max(0, api_key.daily_quota - today_usage),
                "quota_percent_used": round(today_usage / api_key.daily_quota * 100, 2) if api_key.daily_quota > 0 else 0
            },
            "rate_limit": {
                "limit_per_minute": api_key.rate_limit,
                "current_minute_usage": current_minute_usage,
                "remaining": max(0, api_key.rate_limit - current_minute_usage)
            },
            "daily_breakdown": [
                {
                    "date": stat.date.strftime("%Y-%m-%d"),
                    "total": stat.total_requests,
                    "successful": stat.successful_requests,
                    "failed": stat.failed_requests
                }
                for stat in daily_stats
            ],
            "top_endpoints": [
                {"endpoint": ep, "count": count}
                for ep, count in top_endpoints
            ]
        }

    def get_all_keys_stats(self, tenant_id: int) -> List[Dict[str, Any]]:
        """Get summary statistics for all API keys in a tenant."""
        api_keys = self.db.query(APIKey).filter(
            APIKey.tenant_id == tenant_id
        ).all()

        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        results = []

        for key in api_keys:
            # Today's usage
            today_usage = self.db.query(APIKeyUsage).filter(
                APIKeyUsage.api_key_id == key.id,
                APIKeyUsage.created_at >= today
            ).count()

            # Total usage (all time)
            total_usage = self.db.query(APIKeyUsage).filter(
                APIKeyUsage.api_key_id == key.id
            ).count()

            # Last 7 days
            week_ago = today - timedelta(days=7)
            week_usage = self.db.query(APIKeyUsage).filter(
                APIKeyUsage.api_key_id == key.id,
                APIKeyUsage.created_at >= week_ago
            ).count()

            results.append({
                "id": key.id,
                "name": key.name,
                "key_prefix": key.key_prefix,
                "is_active": key.is_active,
                "rate_limit": key.rate_limit,
                "daily_quota": key.daily_quota,
                "restrict_to_templates": key.restrict_to_templates,
                "allowed_template_count": len(key.allowed_templates) if key.restrict_to_templates else None,
                "created_at": key.created_at.isoformat(),
                "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None,
                "usage": {
                    "today": today_usage,
                    "today_quota_percent": round(today_usage / key.daily_quota * 100, 2) if key.daily_quota > 0 else 0,
                    "week": week_usage,
                    "total": total_usage,
                    "current_minute": rate_limiter.get_current_minute_usage(key.id)
                }
            })

        return results
