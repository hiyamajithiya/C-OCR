"""
URL configuration for analytics dashboard endpoints.
"""

from django.urls import path

from api_keys.analytics_views import (
    AnalyticsOverviewView,
    AnalyticsUsageView,
    AnalyticsTopEntitiesView,
    AnalyticsRevenueView,
    AnalyticsEndpointsView,
    AnalyticsErrorsView,
)

urlpatterns = [
    path("overview", AnalyticsOverviewView.as_view(), name="analytics-overview"),
    path("usage", AnalyticsUsageView.as_view(), name="analytics-usage"),
    path("top-entities", AnalyticsTopEntitiesView.as_view(), name="analytics-top-entities"),
    path("revenue", AnalyticsRevenueView.as_view(), name="analytics-revenue"),
    path("endpoints", AnalyticsEndpointsView.as_view(), name="analytics-endpoints"),
    path("errors", AnalyticsErrorsView.as_view(), name="analytics-errors"),
]
