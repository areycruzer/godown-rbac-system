"""
Dynamic RBAC models — Permission, Role, and UserTenantRole.

Permission: Global registry of atomic actions (e.g. "grn:create").
Role:       Tenant-scoped, links to many Permissions, supports hierarchy via weight.
UserTenantRole: Junction linking User ↔ Tenant ↔ Role.
"""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class Permission(models.Model):
    """
    Global registry of atomic permission codes.

    Not tenant-scoped — the same permission codes are shared across all tenants.
    Each tenant's Roles select which permissions they grant.

    Examples::

        code="grn:create"   description="Create a Goods Received Note"
        code="po:approve"   description="Approve a Purchase Order"
        code="user:invite"  description="Invite a new user to the tenant"
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text='Dot/colon-separated action code, e.g. "grn:create".',
    )
    description = models.TextField(blank=True, help_text="Human-readable description.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["code"]

    def __str__(self) -> str:
        return self.code


class Role(models.Model):
    """
    Tenant-scoped role with a set of granted permissions.

    System-seeded roles (``is_default=True``) are created automatically for
    every new tenant (owner, admin, member).  Tenants may also create custom
    roles with arbitrary permission sets.

    ``weight`` provides a simple numeric hierarchy for "at least X" checks:
        owner=30, admin=20, member=10.  Custom roles default to 0.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="roles",
    )
    name = models.CharField(max_length=100, help_text="Display name, e.g. 'Admin'.")
    slug = models.SlugField(
        max_length=100,
        help_text="URL-safe identifier, e.g. 'admin'.",
    )
    is_default = models.BooleanField(
        default=False,
        help_text="True for system-seeded roles that should not be deleted.",
    )
    weight = models.PositiveIntegerField(
        default=0,
        help_text="Hierarchy weight — higher is more privileged.",
    )
    permissions = models.ManyToManyField(
        Permission,
        blank=True,
        related_name="roles",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("tenant", "slug")
        ordering = ["-weight", "name"]
        indexes = [
            models.Index(fields=["tenant", "slug"], name="rbac_role_tenant_slug_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.tenant})"


# Default role slugs and weights — used by seed logic and backward-compat checks.
DEFAULT_ROLES: dict[str, dict[str, int | str]] = {
    "owner": {"name": "Owner", "weight": 30},
    "admin": {"name": "Admin", "weight": 20},
    "member": {"name": "Member", "weight": 10},
}


class UserTenantRole(models.Model):
    """
    Maps a user to a role within a specific tenant.

    Unique per (user, tenant) pair — a user can only hold one role per tenant.
    Roles do NOT transfer across tenants.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tenant_roles",
    )
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="user_roles",
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="role_assignments_made",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        unique_together = ("user", "tenant")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "role"], name="rbac_tenant_role_idx"),
            models.Index(fields=["user", "tenant"], name="rbac_user_tenant_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.user} — {self.role.name} in {self.tenant}"
