from django.urls import path

from apps.rbac.views import (
    AssignRoleView,
    PermissionListView,
    RevokeRoleView,
    RoleCreateView,
    RoleDefinitionListView,
    TenantRoleListView,
    UserAuthContextView,
)

urlpatterns = [
    # Global permission registry
    path("permissions/", PermissionListView.as_view(), name="rbac-permission-list"),
    # Tenant-scoped role definitions
    path(
        "<uuid:tenant_id>/role-definitions/",
        RoleDefinitionListView.as_view(),
        name="rbac-role-definition-list",
    ),
    path(
        "<uuid:tenant_id>/role-definitions/create/",
        RoleCreateView.as_view(),
        name="rbac-role-create",
    ),
    # Tenant-scoped role assignments (memberships)
    path("<uuid:tenant_id>/roles/", TenantRoleListView.as_view(), name="rbac-role-list"),
    path("<uuid:tenant_id>/roles/assign/", AssignRoleView.as_view(), name="rbac-role-assign"),
    path("<uuid:tenant_id>/roles/revoke/", RevokeRoleView.as_view(), name="rbac-role-revoke"),
    # Current user auth context
    path("<uuid:tenant_id>/me/", UserAuthContextView.as_view(), name="rbac-user-context"),
]
