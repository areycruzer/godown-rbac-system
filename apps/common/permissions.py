from rest_framework.permissions import BasePermission
from services.features import FeatureService
from services.rbac import RBACService


class IsTenantAuthorized(BasePermission):
    """
    A unified permission class that checks both feature gates and RBAC permissions.

    Checks two optional view-level attributes:
    - ``required_feature``: e.g. 'procurement_v2_enabled'
    - ``required_permission``: e.g. 'po:approve'

    If either check fails, permission is denied (returns False).
    If a required attribute is missing or None, that check is bypassed.
    Requires that a tenant has been resolved (typically by TenantMiddleware).
    """

    def has_permission(self, request, view) -> bool:
        tenant = getattr(request, "tenant", None)
        if tenant is None:
            return False

        # 1. Feature flag gate check
        required_feature = getattr(view, "required_feature", None)
        if required_feature:
            if not FeatureService.is_feature_active(tenant, required_feature):
                return False

        # 2. RBAC permission gate check
        required_permission = getattr(view, "required_permission", None)
        if required_permission:
            if not RBACService.has_permission(request.user, tenant, required_permission):
                return False

        return True
