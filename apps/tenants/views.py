from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from services.features import FeatureService

from apps.rbac.permissions import HasRolePermission
from apps.tenants.models import Tenant


class TenantFeatureListView(APIView):
    """
    GET /api/v1/tenants/<tenant_id>/features/

    List active feature flags for a tenant.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Tenants"],
        summary="List active features for a tenant",
        responses={200: list[str]},
    )
    def get(self, request, tenant_id):
        tenant = get_object_or_404(Tenant, id=tenant_id)
        features = FeatureService.get_active_features(tenant)
        return Response(features)


class ToggleTenantFeatureView(APIView):
    """
    POST /api/v1/tenants/<tenant_id>/features/toggle/

    Toggle (enable/disable) a feature flag for a tenant.
    Requires owner or admin role.
    """

    permission_classes = [IsAuthenticated, HasRolePermission]
    required_roles = ["owner", "admin"]

    @extend_schema(
        tags=["Tenants"],
        summary="Toggle a feature flag for a tenant",
        request=dict,
        responses={200: dict},
    )
    def post(self, request, tenant_id):
        tenant = get_object_or_404(Tenant, id=tenant_id)
        name = request.data.get("name")
        is_active = request.data.get("is_active", False)
        if not name:
            return Response({"detail": "Feature name is required."}, status=400)

        flag = FeatureService.set_feature(tenant, name, is_active)
        return Response(
            {
                "id": str(flag.id),
                "name": flag.name,
                "is_active": flag.is_active,
                "tenant_id": str(flag.tenant.id) if flag.tenant else None,
            }
        )

