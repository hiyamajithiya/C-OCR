from django.urls import path
from .views import (
    TemplateListCreateView,
    TemplateVersionListCreateView,
    ApplyTemplateView,
    DocumentExtractionsView,
    TemplateDeleteView,
)

urlpatterns = [
    path("", TemplateListCreateView.as_view()),
    path("extractions/document/<int:document_id>", DocumentExtractionsView.as_view()),
    path("<int:template_id>/versions", TemplateVersionListCreateView.as_view()),
    path("<int:template_id>/apply", ApplyTemplateView.as_view()),
    path("<int:template_id>", TemplateDeleteView.as_view()),
]
