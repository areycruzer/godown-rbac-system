"""RBAC use-cases — no HTTP dependencies."""

from __future__ import annotations

from typing import Any

import structlog
from apps.rbac.models import DEFAULT_ROLES, Permission, Role, UserTenantRole
from apps.tenants.models import Tenant
from django.contrib.auth.models import AbstractBaseUser
from django.db import transaction

from services.exceptions import (
    ConflictServiceError,
    NotFoundServiceError,
    ValidationServiceError,
)

log = structlog.get_logger(__name__)


class RBACService:
    """Stateless service for role assignment, permission checks, and role management."""

    # ------------------------------------------------------------------
    # Role management
    # ------------------------------------------------------------------

    @staticmethod
    def create_default_roles(tenant: Tenant) -> list[Role]:
        """
        Create the three system-seeded roles (owner, admin, member) for a tenant.

        Safe to call multiple times — skips roles that already exist.
        Returns the list of created (or existing) Role objects.
        """
        roles: list[Role] = []
        for slug, meta in DEFAULT_ROLES.items():
            role, _created = Role.objects.get_or_create(
                tenant=tenant,
                slug=slug,
                defaults={
                    "name": str(meta["name"]),
                    "weight": int(meta["weight"]),
                    "is_default": True,
                },
            )
            roles.append(role)
        return roles

    @staticmethod
    def create_role(
        tenant: Tenant,
        *,
        name: str,
        slug: str,
        weight: int = 0,
        permission_codes: list[str] | None = None,
    ) -> Role:
        """
        Create a custom role for a tenant.

        Raises ``ConflictServiceError`` if the slug is already taken in this tenant.
        Raises ``ValidationServiceError`` if any permission code doesn't exist.
        """
        if Role.objects.filter(tenant=tenant, slug=slug).exists():
            raise ConflictServiceError(
                f"Role with slug '{slug}' already exists in tenant '{tenant.name}'."
            )

        role = Role.objects.create(
            tenant=tenant,
            name=name,
            slug=slug,
            weight=weight,
            is_default=False,
        )

        if permission_codes:
            permissions = Permission.objects.filter(code__in=permission_codes)
            found_codes = set(permissions.values_list("code", flat=True))
            missing = set(permission_codes) - found_codes
            if missing:
                role.delete()
                raise ValidationServiceError(
                    f"Unknown permission code(s): {', '.join(sorted(missing))}"
                )
            role.permissions.set(permissions)

        return role

    # ------------------------------------------------------------------
    # Permission management
    # ------------------------------------------------------------------

    @staticmethod
    def create_permission(code: str, description: str = "") -> Permission:
        """Create a global permission. Raises ``ConflictServiceError`` if code exists."""
        if Permission.objects.filter(code=code).exists():
            raise ConflictServiceError(f"Permission '{code}' already exists.")
        return Permission.objects.create(code=code, description=description)

    @staticmethod
    def get_or_create_permission(code: str, description: str = "") -> Permission:
        """Get or create a global permission by code."""
        perm, _created = Permission.objects.get_or_create(
            code=code, defaults={"description": description}
        )
        return perm

    # ------------------------------------------------------------------
    # Role assignment / revocation
    # ------------------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def assign_role(
        user: AbstractBaseUser,
        tenant: Tenant,
        role_slug: str,
        *,
        assigned_by: AbstractBaseUser | None = None,
    ) -> UserTenantRole:
        """
        Assign a role (by slug) to a user in a tenant.

        If the user already has a role in this tenant it is updated.
        Raises ``NotFoundServiceError`` if the role slug doesn't exist for this tenant.
        """
        try:
            role = Role.objects.get(tenant=tenant, slug=role_slug)
        except Role.DoesNotExist:
            raise NotFoundServiceError(
                f"Role '{role_slug}' not found in tenant '{tenant.name}'. "
                f"Available: {', '.join(Role.objects.filter(tenant=tenant).values_list('slug', flat=True))}"
            ) from None

        obj, _ = UserTenantRole.objects.update_or_create(
            user_id=user.pk,
            tenant=tenant,
            defaults={
                "role": role,
                "assigned_by_id": assigned_by.pk if assigned_by else None,
            },
        )

        from apps.audit.models import AuditLog  # noqa: PLC0415

        from services.audit import AuditService  # noqa: PLC0415

        AuditService.log(
            AuditLog.Action.ROLE_ASSIGNED,
            tenant=tenant,
            actor=assigned_by,
            resource_type="User",
            resource_id=str(user.pk),
            metadata={"role": role_slug, "target_email": getattr(user, "email", "")},
        )
        return obj

    @staticmethod
    def revoke_role(user: AbstractBaseUser, tenant: Tenant) -> bool:
        """
        Remove user's role from tenant.

        Returns ``True`` if a role was deleted, ``False`` if none existed.
        """
        deleted, _ = UserTenantRole.objects.filter(user_id=user.pk, tenant=tenant).delete()
        if deleted:
            from apps.audit.models import AuditLog  # noqa: PLC0415

            from services.audit import AuditService  # noqa: PLC0415

            AuditService.log(
                AuditLog.Action.ROLE_REVOKED,
                tenant=tenant,
                resource_type="User",
                resource_id=str(user.pk),
                metadata={"target_email": getattr(user, "email", "")},
            )
        return bool(deleted)

    # ------------------------------------------------------------------
    # Query — role checks
    # ------------------------------------------------------------------

    @staticmethod
    def get_role(user: AbstractBaseUser, tenant: Tenant) -> str | None:
        """Return the user's role slug in tenant, or ``None``."""
        try:
            utr = UserTenantRole.objects.select_related("role").get(user_id=user.pk, tenant=tenant)
            return utr.role.slug
        except UserTenantRole.DoesNotExist:
            return None

    @staticmethod
    def get_role_object(user: AbstractBaseUser, tenant: Tenant) -> Role | None:
        """Return the user's Role object in tenant, or ``None``."""
        try:
            utr = UserTenantRole.objects.select_related("role").get(user_id=user.pk, tenant=tenant)
            return utr.role
        except UserTenantRole.DoesNotExist:
            return None

    @staticmethod
    def has_role(
        user: AbstractBaseUser | None,
        tenant: Tenant,
        roles: list[str],
    ) -> bool:
        """
        Return ``True`` iff user holds one of the given role slugs in tenant.

        Django superusers are implicitly granted all roles across all tenants.
        """
        if not user or not getattr(user, "is_authenticated", False):
            return False
        if getattr(user, "is_superuser", False):
            return True
        return UserTenantRole.objects.filter(
            user_id=user.pk, tenant=tenant, role__slug__in=roles
        ).exists()

    # ------------------------------------------------------------------
    # Query — permission checks
    # ------------------------------------------------------------------

    @staticmethod
    def has_permission(
        user: AbstractBaseUser | None,
        tenant: Tenant,
        permission_code: str,
    ) -> bool:
        """
        Return ``True`` iff user's role in tenant grants the given permission code.

        Superusers bypass all permission checks.
        """
        if not user or not getattr(user, "is_authenticated", False):
            return False
        if getattr(user, "is_superuser", False):
            return True
        return UserTenantRole.objects.filter(
            user_id=user.pk,
            tenant=tenant,
            role__permissions__code=permission_code,
        ).exists()

    @staticmethod
    def get_user_permissions(
        user: AbstractBaseUser,
        tenant: Tenant,
    ) -> list[str]:
        """Return all permission codes the user has in a tenant via their role."""
        try:
            utr = UserTenantRole.objects.select_related("role").get(user_id=user.pk, tenant=tenant)
            return list(utr.role.permissions.values_list("code", flat=True))
        except UserTenantRole.DoesNotExist:
            return []

    @staticmethod
    def get_user_auth_context(
        user: AbstractBaseUser,
        tenant: Tenant,
    ) -> dict[str, Any]:
        """
        Return a combined auth context for the user in a tenant.

        Used by the /me/ endpoint to power frontend permission checks.
        Returns role info + permission codes.
        """
        try:
            utr = UserTenantRole.objects.select_related("role").get(user_id=user.pk, tenant=tenant)
            permissions = list(utr.role.permissions.values_list("code", flat=True))
            return {
                "role": {
                    "id": str(utr.role.id),
                    "name": utr.role.name,
                    "slug": utr.role.slug,
                    "weight": utr.role.weight,
                },
                "permissions": permissions,
            }
        except UserTenantRole.DoesNotExist:
            return {
                "role": None,
                "permissions": [],
            }
