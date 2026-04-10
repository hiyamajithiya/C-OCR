from django.urls import path
from .views import (
    SubmitCorrectionView,
    BulkCorrectionView,
    DocumentCorrectionsView,
    TemplateAccuracyView,
    AbbreviationListCreateView,
    AbbreviationDeleteView,
    ProcessLearningView,
)

urlpatterns = [
    path("submit", SubmitCorrectionView.as_view()),
    path("submit-bulk", BulkCorrectionView.as_view()),
    path("document/<int:document_id>", DocumentCorrectionsView.as_view()),
    path("template/<int:template_id>/stats", TemplateAccuracyView.as_view()),
    path("abbreviations", AbbreviationListCreateView.as_view()),
    path("abbreviations/<int:abbreviation_id>", AbbreviationDeleteView.as_view()),
    path("process-learning", ProcessLearningView.as_view()),
]
