"""Demo tenant and user seeding — no HTTP dependencies."""

from __future__ import annotations

import threading
from dataclasses import dataclass

from apps.tenants.models import Domain, Tenant
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.db import transaction
from examples.demo_config import DEMO_ADMIN, DEMO_TENANTS

from services.rbac import RBACService

# Set .active=True while seed() runs so the conftest post_save signal does not
# create an extra test-tenant role for demo users.
_seeding = threading.local()

User = get_user_model()


@dataclass(frozen=True)
class DemoSeedResult:
    tenants: tuple[Tenant, ...]
    admin_user: AbstractUser


class DemoSeedService:
    """Idempotent demo data for local development and API exploration."""

    @staticmethod
    @transaction.atomic
    def seed() -> DemoSeedResult:
        _seeding.active = True
        try:
            # 1. Seed global permissions registry
            permissions = DemoSeedService._ensure_permissions()
            
            # 2. Seed tenants and set default roles + permissions mapping
            tenants = tuple(DemoSeedService._ensure_tenants(permissions))
            
            admin_user = DemoSeedService._ensure_admin_user()
            tenant1 = next(t for t in tenants if t.slug == "tenant1")
            RBACService.assign_role(admin_user, tenant1, "admin")
            return DemoSeedResult(tenants=tenants, admin_user=admin_user)
        finally:
            _seeding.active = False

    @staticmethod
    def _ensure_permissions() -> dict[str, Permission]:
        # Define default permissions to seed
        permissions_data = [
            ("user:invite", "Invite a new user to the tenant"),
            ("po:create", "Create a Purchase Order"),
            ("po:approve", "Approve a Purchase Order"),
            ("grn:create", "Create a Goods Received Note"),
            ("audit:view", "View the tenant audit logs"),
            ("feature:toggle", "Toggle tenant feature flags"),
        ]
        
        perms = {}
        for code, desc in permissions_data:
            perm = RBACService.get_or_create_permission(code, desc)
            perms[code] = perm
        return perms

    @staticmethod
    def _ensure_tenants(permissions: dict[str, Permission]) -> list[Tenant]:
        # Define roles to permissions mapping
        role_permissions_mapping = {
            "owner": [
                "user:invite",
                "po:create",
                "po:approve",
                "grn:create",
                "audit:view",
                "feature:toggle",
            ],
            "admin": [
                "user:invite",
                "po:create",
                "grn:create",
                "audit:view",
            ],
            "member": [
                "po:create",
                "grn:create",
            ],
        }

        tenants: list[Tenant] = []
        for spec in DEMO_TENANTS:
            tenant, _ = Tenant.objects.update_or_create(
                id=spec.id,
                defaults={
                    "name": spec.name,
                    "slug": spec.slug,
                    "schema_name": spec.slug,
                },
            )
            Domain.objects.update_or_create(
                tenant=tenant,
                domain=f"{spec.slug}.localhost",
                defaults={"is_primary": True},
            )
            
            # Create default roles
            roles = RBACService.create_default_roles(tenant)
            
            # Map permissions to roles
            for role in roles:
                allowed_codes = role_permissions_mapping.get(role.slug, [])
                role_perms = [permissions[code] for code in allowed_codes if code in permissions]
                role.permissions.set(role_perms)

            tenants.append(tenant)
        return tenants

    @staticmethod
    def _ensure_admin_user() -> AbstractUser:
        user, _ = User.objects.get_or_create(
            username=DEMO_ADMIN.username,
            defaults={
                "email": DEMO_ADMIN.email,
                "first_name": DEMO_ADMIN.first_name,
                "last_name": DEMO_ADMIN.last_name,
            },
        )
        user.email = DEMO_ADMIN.email
        user.first_name = DEMO_ADMIN.first_name
        user.last_name = DEMO_ADMIN.last_name
        user.set_password(DEMO_ADMIN.password)
        user.save()
        return user

