"""
URL patterns for /api/v1/auth/
"""

from django.urls import path

from accounts.views import LoginView, RefreshView

urlpatterns = [
    path("login", LoginView.as_view()),
    path("refresh", RefreshView.as_view()),
]
