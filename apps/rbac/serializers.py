from __future__ import annotations

from typing import Any

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from rest_framework import serializers

from apps.rbac.models import Permission, Role, UserTenantRole

User = get_user_model()


class PermissionSerializer(serializers.ModelSerializer):  # type: ignore[type-arg]
    class Meta:
        model = Permission
        fields = ("id", "code", "description")
        read_only_fields = fields


class RoleSerializer(serializers.ModelSerializer):  # type: ignore[type-arg]
    permissions = PermissionSerializer(many=True, read_only=True)

    class Meta:
        model = Role
        fields = ("id", "name", "slug", "is_default", "weight", "permissions", "created_at")
        read_only_fields = ("id", "is_default", "created_at")


class RoleCreateSerializer(serializers.Serializer):  # type: ignore[type-arg]
    name = serializers.CharField(max_length=100, help_text="Display name for the role.")
    slug = serializers.SlugField(max_length=100, help_text="URL-safe identifier.")
    weight = serializers.IntegerField(
        default=0, min_value=0, help_text="Hierarchy weight (higher = more privileged)."
    )
    permission_codes = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        default=list,
        help_text="List of permission codes to grant to this role.",
    )


class UserTenantRoleSerializer(serializers.ModelSerializer):  # type: ignore[type-arg]
    username = serializers.CharField(source="user.username", read_only=True)
    tenant_name = serializers.CharField(source="tenant.name", read_only=True)
    role_name = serializers.CharField(source="role.name", read_only=True)
    role_slug = serializers.CharField(source="role.slug", read_only=True)

    class Meta:
        model = UserTenantRole
        fields = ("id", "username", "tenant_name", "role_name", "role_slug", "created_at")
        read_only_fields = fields


class RoleAssignSerializer(serializers.Serializer):  # type: ignore[type-arg]
    user_id = serializers.IntegerField(help_text="PK of the user to assign the role to.")
    role = serializers.SlugField(
        max_length=100,
        help_text="Role slug, e.g. 'admin', 'member', or a custom role slug.",
    )

    def validate_user_id(self, value: int) -> AbstractUser:
        try:
            return User.objects.get(pk=value)
        except User.DoesNotExist as exc:
            raise serializers.ValidationError("User not found.") from exc


class RoleRevokeSerializer(serializers.Serializer):  # type: ignore[type-arg]
    user_id = serializers.IntegerField(help_text="PK of the user whose role to revoke.")

    def validate_user_id(self, value: int) -> Any:
        try:
            return User.objects.get(pk=value)
        except User.DoesNotExist as exc:
            raise serializers.ValidationError("User not found.") from exc


class UserAuthContextSerializer(serializers.Serializer):  # type: ignore[type-arg]
    """Serializer for the /me/ auth context response."""

    role = RoleSerializer(read_only=True, allow_null=True)
    permissions = serializers.ListField(child=serializers.CharField(), read_only=True)
    features = serializers.ListField(child=serializers.CharField(), read_only=True)
