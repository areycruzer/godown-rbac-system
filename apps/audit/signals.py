from __future__ import annotations

from django.db.models.signals import post_delete, post_save, pre_save

from apps.audit.context import get_audit_context


def audit_pre_save(sender, instance, **kwargs):
    """Capture the old state of the instance before saving to compute changes later."""
    if instance.pk:
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            instance._old_values = {
                field.name: field.value_to_string(old_instance) for field in sender._meta.fields
            }
        except sender.DoesNotExist:
            instance._old_values = {}
    else:
        instance._old_values = {}


def audit_post_save(sender, instance, created, **kwargs):
    """Compute changes and queue the Celery write_audit_log task."""
    ctx = get_audit_context()
    action = "create" if created else "update"

    changes = {}
    if created:
        after_vals = {
            field.name: field.value_to_string(instance)
            for field in sender._meta.fields
            if field.name != "password"
        }
        changes = {"after": after_vals}
    else:
        old_vals = getattr(instance, "_old_values", {})
        before_vals = {}
        after_vals = {}
        for field in sender._meta.fields:
            if field.name == "password":
                continue
            new_val = field.value_to_string(instance)
            old_val = old_vals.get(field.name)
            if old_val != new_val:
                before_vals[field.name] = old_val
                after_vals[field.name] = new_val
        if before_vals or after_vals:
            changes = {"before": before_vals, "after": after_vals}
        else:
            # No actual changes
            return

    tenant_id = None
    if hasattr(instance, "tenant_id") and instance.tenant_id:
        tenant_id = str(instance.tenant_id)
    elif hasattr(instance, "tenant") and instance.tenant:
        tenant_id = str(instance.tenant.id)
    elif ctx.get("tenant"):
        tenant_id = str(ctx["tenant"].id)

    actor_id = None
    actor_email = ""
    user = ctx.get("user")
    if user and getattr(user, "is_authenticated", False):
        actor_id = user.id
        actor_email = user.email

    from apps.audit.tasks import write_audit_log

    write_audit_log.delay(
        action=action,
        tenant_id=tenant_id,
        actor_id=actor_id,
        actor_email=actor_email,
        resource_type=sender.__name__,
        resource_id=str(instance.pk),
        metadata={},
        changes=changes,
        ip_address=ctx.get("ip_address"),
        user_agent=ctx.get("user_agent", ""),
    )


def audit_post_delete(sender, instance, **kwargs):
    """Queue audit log on deletion."""
    ctx = get_audit_context()

    before_vals = {
        field.name: field.value_to_string(instance)
        for field in sender._meta.fields
        if field.name != "password"
    }
    changes = {"before": before_vals}

    tenant_id = None
    if hasattr(instance, "tenant_id") and instance.tenant_id:
        tenant_id = str(instance.tenant_id)
    elif hasattr(instance, "tenant") and instance.tenant:
        tenant_id = str(instance.tenant.id)
    elif ctx.get("tenant"):
        tenant_id = str(ctx["tenant"].id)

    actor_id = None
    actor_email = ""
    user = ctx.get("user")
    if user and getattr(user, "is_authenticated", False):
        actor_id = user.id
        actor_email = user.email

    from apps.audit.tasks import write_audit_log

    write_audit_log.delay(
        action="delete",
        tenant_id=tenant_id,
        actor_id=actor_id,
        actor_email=actor_email,
        resource_type=sender.__name__,
        resource_id=str(instance.pk),
        metadata={},
        changes=changes,
        ip_address=ctx.get("ip_address"),
        user_agent=ctx.get("user_agent", ""),
    )


def connect_audit_signals():
    """Connect pre_save, post_save, and post_delete signals to models to audit."""
    from apps.rbac.models import Role, UserTenantRole
    from apps.tenants.models import FeatureFlag

    models_to_audit = [Role, UserTenantRole, FeatureFlag]
    for model in models_to_audit:
        pre_save.connect(
            audit_pre_save,
            sender=model,
            dispatch_uid=f"audit_pre_{model.__name__}",
        )
        post_save.connect(
            audit_post_save,
            sender=model,
            dispatch_uid=f"audit_post_{model.__name__}",
        )
        post_delete.connect(
            audit_post_delete,
            sender=model,
            dispatch_uid=f"audit_delete_{model.__name__}",
        )
