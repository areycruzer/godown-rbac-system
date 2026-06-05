import pytest
from apps.audit.context import _audit_context
from apps.audit.models import AuditLog
from apps.tenants.models import FeatureFlag, Tenant
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(name="Audit Corp", slug="audit", schema_name="audit")


@pytest.fixture
def user(db):
    return User.objects.create_user(username="auditor", email="auditor@example.com")


@pytest.mark.django_db
def test_create_signals_audit_log(tenant, user):
    # Set thread local context
    _audit_context.user = user
    _audit_context.tenant = tenant
    _audit_context.ip_address = "127.0.0.1"

    try:
        # Create a model registered for auditing (FeatureFlag)
        flag = FeatureFlag.objects.create(tenant=tenant, name="po_v2", is_active=True)

        # Retrieve the generated AuditLog record
        audit = AuditLog.objects.filter(
            resource_type="FeatureFlag", resource_id=str(flag.pk)
        ).first()
        assert audit is not None
        assert audit.action == "create"
        assert audit.tenant == tenant
        assert audit.actor == user
        assert audit.actor_email == "auditor@example.com"
        assert audit.ip_address == "127.0.0.1"
        assert audit.changes["after"]["name"] == "po_v2"
        assert audit.changes["after"]["is_active"] == "True"
    finally:
        _audit_context.user = None
        _audit_context.tenant = None
        _audit_context.ip_address = None


@pytest.mark.django_db
def test_update_signals_audit_log(tenant, user):
    flag = FeatureFlag.objects.create(tenant=tenant, name="po_v2", is_active=False)

    # Clear logs created by creation
    AuditLog.objects.all().delete()

    _audit_context.user = user
    _audit_context.tenant = tenant

    try:
        # Update flag
        flag.is_active = True
        flag.save()

        # AuditLog record should exist for update
        audit = AuditLog.objects.filter(
            resource_type="FeatureFlag", resource_id=str(flag.pk)
        ).first()
        assert audit is not None
        assert audit.action == "update"
        assert audit.changes["before"]["is_active"] == "False"
        assert audit.changes["after"]["is_active"] == "True"
    finally:
        _audit_context.user = None
        _audit_context.tenant = None


@pytest.mark.django_db
def test_delete_signals_audit_log(tenant, user):
    flag = FeatureFlag.objects.create(tenant=tenant, name="po_v2", is_active=True)

    # Clear creation logs
    AuditLog.objects.all().delete()

    _audit_context.user = user
    _audit_context.tenant = tenant

    try:
        flag_id = str(flag.pk)
        flag.delete()

        audit = AuditLog.objects.filter(resource_type="FeatureFlag", resource_id=flag_id).first()
        assert audit is not None
        assert audit.action == "delete"
        assert audit.changes["before"]["name"] == "po_v2"
    finally:
        _audit_context.user = None
        _audit_context.tenant = None
