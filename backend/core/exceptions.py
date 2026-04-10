"""
Custom exception handler to match FastAPI's error response format.
"""

import structlog
from django.conf import settings
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

logger = structlog.get_logger()


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is None:
        logger.error("unhandled_exception", error=str(exc), exc_info=True)
        detail = str(exc) if settings.DEBUG else "An internal error occurred"
        return Response(
            {"detail": detail},
            status=500,
        )

    # Transform DRF validation errors to FastAPI-compatible 422 format
    if isinstance(exc, ValidationError):
        detail_list = []
        if isinstance(exc.detail, dict):
            for field, errors in exc.detail.items():
                if isinstance(errors, list):
                    for err in errors:
                        detail_list.append({
                            "loc": ["body", field],
                            "msg": str(err),
                            "type": "value_error",
                        })
                else:
                    detail_list.append({
                        "loc": ["body", field],
                        "msg": str(errors),
                        "type": "value_error",
                    })
        elif isinstance(exc.detail, list):
            for err in exc.detail:
                detail_list.append({
                    "loc": ["body"],
                    "msg": str(err),
                    "type": "value_error",
                })
        else:
            detail_list.append({
                "loc": ["body"],
                "msg": str(exc.detail),
                "type": "value_error",
            })
        response.status_code = 422
        response.data = {"detail": detail_list}

    return response
