from django.urls import path
from .views import AuditLogListView, AuditLogDetailView

urlpatterns = [
    path("", AuditLogListView.as_view()),
    path("<int:log_id>", AuditLogDetailView.as_view()),
]
