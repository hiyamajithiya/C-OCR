"""
URL patterns for /api/v1/users/
"""

from django.urls import path

from accounts.views import UserListCreateView, UserMeView, UserUpdateView

urlpatterns = [
    path("", UserListCreateView.as_view()),
    path("me", UserMeView.as_view()),
    path("<int:user_id>", UserUpdateView.as_view()),
]
