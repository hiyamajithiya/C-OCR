"""
Custom middleware for request tracking and observability.
"""

import time
import uuid
import structlog

logger = structlog.get_logger()


class RequestIDMiddleware:
    """Add unique X-Request-ID to every request/response and log request metrics."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = request.META.get("HTTP_X_REQUEST_ID", str(uuid.uuid4()))
        request.request_id = request_id

        start_time = time.time()
        response = self.get_response(request)
        duration_ms = int((time.time() - start_time) * 1000)

        response["X-Request-ID"] = request_id

        # Log request metrics (skip health checks and static)
        path = request.path
        if path not in ("/health", "/") and not path.startswith("/static"):
            logger.info(
                "request_completed",
                request_id=request_id,
                method=request.method,
                path=path,
                status=response.status_code,
                duration_ms=duration_ms,
                ip=request.META.get("REMOTE_ADDR"),
            )

        return response


class RateLimitHeadersMiddleware:
    """
    Adds X-RateLimit-* headers to responses for API-key-authenticated requests.
    Must be placed after authentication has run (i.e. works at the response phase).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Only add headers when the request was authenticated with an API key
        api_key = getattr(request, "api_key", None)
        if api_key is not None:
            from services.api_key_service import rate_limiter

            rate_limit = api_key.rate_limit
            current_usage = rate_limiter.get_current_minute_usage(api_key.id)
            remaining = max(0, rate_limit - current_usage)

            import time
            # Reset = seconds until the current 60-second window expires
            reset_seconds = 60

            response["X-RateLimit-Limit"] = str(rate_limit)
            response["X-RateLimit-Remaining"] = str(remaining)
            response["X-RateLimit-Reset"] = str(int(time.time()) + reset_seconds)

        return response
