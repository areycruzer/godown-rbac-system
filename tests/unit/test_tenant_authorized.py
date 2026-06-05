import pytest
from apps.common.permissions import IsTenantAuthorized
from apps.tenants.models import Tenant
from django.contrib.auth import get_user_model
from services.features import FeatureService
from services.rbac import RBACService

User = get_user_model()


class MockView:
    required_feature = None
    required_permission = None


class MockRequest:
    def __init__(self, user, tenant):
        self.user = user
        self.tenant = tenant


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(name="Auth Corp", slug="authz", schema_name="authz")


@pytest.fixture
def user(db):
    return User.objects.create_user(username="testuser", password="SecurePass123!")


@pytest.mark.django_db
def test_is_tenant_authorized_no_tenant(user):
    request = MockRequest(user=user, tenant=None)
    view = MockView()
    permission = IsTenantAuthorized()

    assert permission.has_permission(request, view) is False


@pytest.mark.django_db
def test_is_tenant_authorized_no_requirements(tenant, user):
    request = MockRequest(user=user, tenant=tenant)
    view = MockView()
    permission = IsTenantAuthorized()

    assert permission.has_permission(request, view) is True


@pytest.mark.django_db
def test_is_tenant_authorized_feature_gate(tenant, user):
    request = MockRequest(user=user, tenant=tenant)
    view = MockView()
    view.required_feature = "premium_billing"
    permission = IsTenantAuthorized()

    # 1. Feature inactive -> False
    assert permission.has_permission(request, view) is False

    # 2. Feature active -> True
    FeatureService.set_feature(None, "premium_billing", is_active=True)
    assert permission.has_permission(request, view) is True


@pytest.mark.django_db
def test_is_tenant_authorized_permission_gate(tenant, user):
    request = MockRequest(user=user, tenant=tenant)
    view = MockView()
    view.required_permission = "po:approve"
    permission = IsTenantAuthorized()

    # 1. User has no role/permission -> False
    assert permission.has_permission(request, view) is False

    # 2. User assigned permission -> True
    RBACService.get_or_create_permission("po:approve")
    RBACService.create_role(
        tenant,
        name="Approver",
        slug="approver",
        permission_codes=["po:approve"],
    )
    RBACService.assign_role(user, tenant, "approver")
    assert permission.has_permission(request, view) is True


@pytest.mark.django_db
def test_is_tenant_authorized_combined_gate(tenant, user):
    request = MockRequest(user=user, tenant=tenant)
    view = MockView()
    view.required_feature = "po_v2"
    view.required_permission = "po:create"
    permission = IsTenantAuthorized()

    # Setup feature and permission
    FeatureService.set_feature(None, "po_v2", is_active=True)
    RBACService.get_or_create_permission("po:create")
    RBACService.create_role(
        tenant,
        name="Creator",
        slug="creator",
        permission_codes=["po:create"],
    )
    RBACService.assign_role(user, tenant, "creator")

    # 1. Both active -> True
    assert permission.has_permission(request, view) is True

    # 2. Turn feature off -> False
    FeatureService.set_feature(None, "po_v2", is_active=False)
    assert permission.has_permission(request, view) is False
