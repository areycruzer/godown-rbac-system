from django.urls import path

from apps.tenants.views import TenantFeatureListView, ToggleTenantFeatureView

urlpatterns = [
    path(
        "<uuid:tenant_id>/features/",
        TenantFeatureListView.as_view(),
        name="tenant-feature-list",
    ),
    path(
        "<uuid:tenant_id>/features/toggle/",
        ToggleTenantFeatureView.as_view(),
        name="tenant-feature-toggle",
    ),
]
