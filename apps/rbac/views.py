from __future__ import annotations

from typing import cast

from django.contrib.auth.models import AbstractBaseUser
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema
from examples.demo_config import TENANT1_ID
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from services.rbac import RBACService

from apps.rbac.models import Permission, Role, UserTenantRole
from apps.rbac.permissions import HasRolePermission
from apps.rbac.serializers import (
    PermissionSerializer,
    RoleAssignSerializer,
    RoleCreateSerializer,
    RoleRevokeSerializer,
    RoleSerializer,
    UserTenantRoleSerializer,
)
from apps.tenants.models import Tenant


class PermissionListView(APIView):
    """
    GET /api/v1/rbac/permissions/

    List all available permission codes (global registry).
    Any authenticated user can read this.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["RBAC"],
        summary="List all permission codes",
        responses={200: PermissionSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        permissions = Permission.objects.all()
        serializer = PermissionSerializer(permissions, many=True)
        return Response(serializer.data)


class TenantRoleListView(APIView):
    """
    GET /api/v1/rbac/<tenant_id>/roles/

    List all role assignments for a tenant.
    Accessible by any authenticated member of the tenant.
    """

    permission_classes = [IsAuthenticated, HasRolePermission]
    required_roles = ["owner", "admin", "member"]

    @extend_schema(
        tags=["RBAC"],
        summary="List role assignments for a tenant",
        description=(
            "Requires membership in the tenant. "
            f"After ``seed_demo``, Tenant One id is ``{TENANT1_ID}``."
        ),
        responses={200: UserTenantRoleSerializer(many=True)},
        parameters=[
            OpenApiParameter(
                "tenant_id",
                OpenApiTypes.UUID,
                OpenApiParameter.PATH,
                description="Tenant workspace UUID",
                examples=[
                    OpenApiExample(
                        "Tenant One ID",
                        value=str(TENANT1_ID),
                    )
                ],
            ),
        ],
    )
    def get(self, request: Request, tenant_id: str) -> Response:
        tenant = get_object_or_404(Tenant, id=tenant_id)
        roles = UserTenantRole.objects.filter(tenant=tenant).select_related(
            "user", "tenant", "role"
        )
        serializer = UserTenantRoleSerializer(roles, many=True)
        return Response(serializer.data)


class RoleDefinitionListView(APIView):
    """
    GET  /api/v1/rbac/<tenant_id>/role-definitions/ — list all role definitions
    POST /api/v1/rbac/<tenant_id>/role-definitions/ — create a custom role
    """

    permission_classes = [IsAuthenticated, HasRolePermission]
    required_roles = ["owner", "admin", "member"]

    @extend_schema(
        tags=["RBAC"],
        summary="List role definitions for a tenant",
        responses={200: RoleSerializer(many=True)},
    )
    def get(self, request: Request, tenant_id: str) -> Response:
        tenant = get_object_or_404(Tenant, id=tenant_id)
        roles = Role.objects.filter(tenant=tenant).prefetch_related("permissions")
        serializer = RoleSerializer(roles, many=True)
        return Response(serializer.data)

    @extend_schema(
        tags=["RBAC"],
        summary="Create a custom role",
        request=RoleCreateSerializer,
        responses={201: RoleSerializer},
    )
    def post(self, request: Request, tenant_id: str) -> Response:
        # Creating roles requires owner or admin (stricter than listing)
        if not RBACService.has_role(request.user, get_object_or_404(Tenant, id=tenant_id), ["owner", "admin"]):
            return Response(
                {"detail": "You do not have the required role to perform this action."},
                status=status.HTTP_403_FORBIDDEN,
            )

        tenant = get_object_or_404(Tenant, id=tenant_id)
        serializer = RoleCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        role = RBACService.create_role(
            tenant,
            name=serializer.validated_data["name"],
            slug=serializer.validated_data["slug"],
            weight=serializer.validated_data.get("weight", 0),
            permission_codes=serializer.validated_data.get("permission_codes"),
        )
        return Response(
            RoleSerializer(role).data,
            status=status.HTTP_201_CREATED,
        )


class AssignRoleView(APIView):
    """
    POST /api/v1/rbac/<tenant_id>/roles/assign/

    Assign (or update) a role for a user within the tenant.
    Requires the caller to be an owner or admin of the tenant.

    Request body::

        { "user_id": 42, "role": "member" }
    """

    permission_classes = [IsAuthenticated, HasRolePermission]
    required_roles = ["owner", "admin"]

    def post(self, request: Request, tenant_id: str) -> Response:
        tenant = get_object_or_404(Tenant, id=tenant_id)
        serializer = RoleAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user_id"]  # validate_user_id returns the User
        role_slug = serializer.validated_data["role"]

        user_role = RBACService.assign_role(
            user, tenant, role_slug, assigned_by=cast(AbstractBaseUser, request.user)
        )
        return Response(
            UserTenantRoleSerializer(user_role).data,
            status=status.HTTP_201_CREATED,
        )


class RevokeRoleView(APIView):
    """Revoke a user's role within a tenant. Requires owner or admin."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    required_roles = ["owner", "admin"]

    @extend_schema(
        tags=["RBAC"],
        request=RoleRevokeSerializer,
        responses={204: None},
        summary="Revoke a role from a user within a tenant",
    )
    def post(self, request: Request, tenant_id: str) -> Response:
        tenant = get_object_or_404(Tenant, pk=tenant_id)
        serializer = RoleRevokeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # validate_user_id already resolves the User object
        user = serializer.validated_data["user_id"]
        RBACService.revoke_role(user, tenant)
        return Response(status=status.HTTP_204_NO_CONTENT)


class UserAuthContextView(APIView):
    """
    GET /api/v1/rbac/<tenant_id>/me/

    Return the current user's role, permissions, and active feature flags
    for the given tenant. Powers the frontend AuthContext provider.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["RBAC"],
        summary="Get current user auth context for a tenant",
        responses={200: dict},
    )
    def get(self, request: Request, tenant_id: str) -> Response:
        tenant = get_object_or_404(Tenant, id=tenant_id)
        user = cast(AbstractBaseUser, request.user)

        auth_context = RBACService.get_user_auth_context(user, tenant)

        # Include active feature flags for this tenant
        from services.features import FeatureService  # noqa: PLC0415

        auth_context["features"] = FeatureService.get_active_features(tenant)

        return Response(auth_context)
