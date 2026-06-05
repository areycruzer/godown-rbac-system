from __future__ import annotations

from typing import Any

from django.contrib.auth import get_user_model

from apps.audit.models import AuditLog
from apps.tenants.models import Tenant
from celery import shared_task


@shared_task(name="apps.audit.tasks.write_audit_log")
def write_audit_log(
    action: str,
    tenant_id: str | None,
    actor_id: int | None,
    actor_email: str,
    resource_type: str,
    resource_id: str,
    metadata: dict[str, Any],
    changes: dict[str, Any],
    ip_address: str | None,
    user_agent: str,
) -> str:
    """Create an AuditLog record asynchronously."""
    tenant = None
    if tenant_id:
        try:
            tenant = Tenant.objects.get(pk=tenant_id)
        except Tenant.DoesNotExist:
            pass

    actor = None
    if actor_id:
        User = get_user_model()
        try:
            actor = User.objects.get(pk=actor_id)
        except User.DoesNotExist:
            pass

    AuditLog.objects.create(
        tenant=tenant,
        actor=actor,
        actor_email=actor_email,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        metadata=metadata,
        changes=changes,
        ip_address=ip_address,
        user_agent=user_agent or "",
    )
    return f"audit_logged:{action}:{resource_type}:{resource_id}"
