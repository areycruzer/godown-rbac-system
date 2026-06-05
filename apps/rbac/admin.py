from django.contrib import admin

from apps.rbac.models import Permission, Role, UserTenantRole


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("code", "description", "created_at")
    search_fields = ("code", "description")
    ordering = ("code",)


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("name", "slug", "tenant", "is_default", "weight", "created_at")
    list_filter = ("is_default", "tenant")
    search_fields = ("name", "slug", "tenant__name")
    filter_horizontal = ("permissions",)
    raw_id_fields = ("tenant",)


@admin.register(UserTenantRole)
class UserTenantRoleAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("user", "tenant", "role", "assigned_by", "created_at")
    list_filter = ("role__slug", "tenant")
    search_fields = ("user__username", "tenant__name", "role__name")
    raw_id_fields = ("user", "tenant", "assigned_by", "role")
