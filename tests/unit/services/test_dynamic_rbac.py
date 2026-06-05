import pytest
from apps.tenants.models import Tenant
from django.contrib.auth import get_user_model
from services.exceptions import ConflictServiceError, ValidationServiceError
from services.rbac import RBACService

User = get_user_model()


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(name="Dynamic Corp", slug="dynamic", schema_name="dynamic")


@pytest.fixture
def user(db):
    return User.objects.create_user(username="testuser", password="SecurePass123!")


@pytest.mark.django_db
def test_create_permission_and_role(tenant):
    # 1. Create permission
    perm = RBACService.get_or_create_permission("grn:create", "Create goods received notes")
    assert perm.code == "grn:create"

    # 2. Create role with permission
    role = RBACService.create_role(
        tenant,
        name="Procurement Officer",
        slug="procurement-officer",
        weight=15,
        permission_codes=["grn:create"],
    )
    assert role.name == "Procurement Officer"
    assert role.slug == "procurement-officer"
    assert role.weight == 15
    assert role.permissions.filter(code="grn:create").exists()


@pytest.mark.django_db
def test_create_role_duplicate_slug_raises(tenant):
    RBACService.create_role(tenant, name="Role One", slug="role-one")
    with pytest.raises(ConflictServiceError):
        RBACService.create_role(tenant, name="Role Two", slug="role-one")


@pytest.mark.django_db
def test_create_role_unknown_permission_raises(tenant):
    with pytest.raises(ValidationServiceError, match="Unknown permission code"):
        RBACService.create_role(tenant, name="Role", slug="role", permission_codes=["invalid:perm"])


@pytest.mark.django_db
def test_has_permission(tenant, user):
    RBACService.get_or_create_permission("po:approve", "Approve PO")
    RBACService.create_role(
        tenant,
        name="Approver",
        slug="approver",
        permission_codes=["po:approve"],
    )
    RBACService.assign_role(user, tenant, "approver")

    assert RBACService.has_permission(user, tenant, "po:approve") is True
    assert RBACService.has_permission(user, tenant, "grn:create") is False
    assert RBACService.get_user_permissions(user, tenant) == ["po:approve"]
