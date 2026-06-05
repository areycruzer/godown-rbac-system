from __future__ import annotations

from apps.tenants.models import FeatureFlag, Tenant


class FeatureService:
    """Service to query, manage and evaluate feature flags."""

    @staticmethod
    def is_feature_active(tenant: Tenant | None, feature_name: str) -> bool:
        """
        Check if a feature is active for a given tenant.

        Priority:
        1. Tenant-specific override (if tenant is provided).
        2. Global flag (tenant=None).
        3. False if neither exists.
        """
        if tenant:
            tenant_flag = FeatureFlag.objects.filter(tenant=tenant, name=feature_name).first()
            if tenant_flag is not None:
                return tenant_flag.is_active

        global_flag = FeatureFlag.objects.filter(tenant=None, name=feature_name).first()
        if global_flag is not None:
            return global_flag.is_active

        return False

    @staticmethod
    def get_active_features(tenant: Tenant | None) -> list[str]:
        """
        Return a list of all active feature names for the tenant.

        Includes active global features unless overridden by the tenant.
        """
        global_flags = {ff.name: ff.is_active for ff in FeatureFlag.objects.filter(tenant=None)}

        if tenant:
            tenant_flags = {
                ff.name: ff.is_active for ff in FeatureFlag.objects.filter(tenant=tenant)
            }
            merged = {**global_flags, **tenant_flags}
        else:
            merged = global_flags

        return [name for name, active in merged.items() if active]

    @staticmethod
    def set_feature(tenant: Tenant | None, name: str, is_active: bool) -> FeatureFlag:
        """Create or update a feature flag toggle."""
        flag, _ = FeatureFlag.objects.update_or_create(
            tenant=tenant,
            name=name,
            defaults={"is_active": is_active},
        )
        return flag
