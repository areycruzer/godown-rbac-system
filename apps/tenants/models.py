import uuid

from django.db import models


class Tenant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, max_length=100)
    schema_name = models.SlugField(unique=True, max_length=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Domain(models.Model):
    """Maps a hostname (e.g. ``tenant1.localhost``) to a Tenant."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="domains")
    domain = models.CharField(max_length=253, unique=True, db_index=True)
    is_primary = models.BooleanField(default=True)

    class Meta:
        ordering = ["domain"]

    def __str__(self) -> str:
        return self.domain


class FeatureFlag(models.Model):
    """
    Simple, context-aware feature toggle.

    When ``tenant`` is NULL the flag is **global** — it applies to all tenants
    unless a tenant-specific override exists.

    Lookup priority (implemented in ``FeatureService.is_feature_active``):
    1. Tenant-specific flag  →  use its ``is_active`` value
    2. Global flag (tenant=NULL)  →  fallback
    3. No flag at all  →  feature is OFF

    Examples::

        FeatureFlag(tenant=None,    name="procurement_v2_enabled", is_active=True)   # global ON
        FeatureFlag(tenant=acme,    name="procurement_v2_enabled", is_active=False)  # OFF for Acme
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="feature_flags",
        help_text="NULL = global flag (applies to all tenants unless overridden).",
    )
    name = models.CharField(
        max_length=100,
        db_index=True,
        help_text='Feature name, e.g. "procurement_v2_enabled".',
    )
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("tenant", "name")
        ordering = ["name"]

    def __str__(self) -> str:
        scope = self.tenant.name if self.tenant else "GLOBAL"
        status = "ON" if self.is_active else "OFF"
        return f"{self.name} [{scope}] = {status}"
