from django.apps import AppConfig


class TenantsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.tenants"

    def ready(self):
        from django.db.models.signals import post_save
        from services.rbac import RBACService

        from apps.tenants.models import Tenant

        def create_tenant_default_roles(sender, instance, created, **kwargs):
            if created:
                RBACService.create_default_roles(instance)

        post_save.connect(
            create_tenant_default_roles,
            sender=Tenant,
            dispatch_uid="create_tenant_default_roles_signal",
        )
