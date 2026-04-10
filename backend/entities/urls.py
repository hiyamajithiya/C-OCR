"""
Admin entity management URL routes.
"""

from django.urls import path

from entities.views import (
    EntityListCreateView,
    EntityDetailUpdateView,
    EntitySuspendView,
    EntityUsageView,
    EntityUserCreateView,
    EntityInvoiceListView,
    GenerateInvoiceView,
)

urlpatterns = [
    path("", EntityListCreateView.as_view()),
    path("<int:entity_id>", EntityDetailUpdateView.as_view()),
    path("<int:entity_id>/suspend", EntitySuspendView.as_view()),
    path("<int:entity_id>/usage", EntityUsageView.as_view()),
    path("<int:entity_id>/users", EntityUserCreateView.as_view()),
    path("<int:entity_id>/invoices", EntityInvoiceListView.as_view()),
    path("<int:entity_id>/generate-invoice", GenerateInvoiceView.as_view()),
]
