from django.urls import path
from .views import (
    APIKeyListCreateView,
    APIKeyWithStatsView,
    APIKeyStatsView,
    APIKeyUpdateStatsView,
    APIKeyTemplatesView,
    APIKeyRevokeView,
)

urlpatterns = [
    path("", APIKeyListCreateView.as_view()),
    path("with-stats", APIKeyWithStatsView.as_view()),
    path("<int:key_id>/stats", APIKeyStatsView.as_view()),
    path("<int:key_id>/update-stats", APIKeyUpdateStatsView.as_view()),
    path("<int:key_id>/templates", APIKeyTemplatesView.as_view()),
    path("<int:key_id>", APIKeyRevokeView.as_view()),
]
