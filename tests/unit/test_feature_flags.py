import pytest
from apps.tenants.models import Tenant
from services.features import FeatureService


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(name="Feature Corp", slug="feature", schema_name="feature")


@pytest.fixture
def other_tenant(db):
    return Tenant.objects.create(name="Other Corp", slug="other", schema_name="other")


@pytest.mark.django_db
def test_global_flag_evaluation(tenant):
    # Setup global flag
    FeatureService.set_feature(None, "billing_v2", is_active=True)

    # Evaluates to True for any tenant
    assert FeatureService.is_feature_active(tenant, "billing_v2") is True
    assert FeatureService.is_feature_active(None, "billing_v2") is True


@pytest.mark.django_db
def test_tenant_override(tenant, other_tenant):
    # Global ON, but tenant-specific OFF
    FeatureService.set_feature(None, "procurement_v2", is_active=True)
    FeatureService.set_feature(tenant, "procurement_v2", is_active=False)

    assert FeatureService.is_feature_active(None, "procurement_v2") is True
    assert FeatureService.is_feature_active(tenant, "procurement_v2") is False
    assert FeatureService.is_feature_active(other_tenant, "procurement_v2") is True


@pytest.mark.django_db
def test_tenant_override_active(tenant, other_tenant):
    # Global OFF, but tenant-specific ON
    FeatureService.set_feature(None, "beta_feature", is_active=False)
    FeatureService.set_feature(tenant, "beta_feature", is_active=True)

    assert FeatureService.is_feature_active(None, "beta_feature") is False
    assert FeatureService.is_feature_active(tenant, "beta_feature") is True
    assert FeatureService.is_feature_active(other_tenant, "beta_feature") is False


@pytest.mark.django_db
def test_unknown_flag_is_inactive(tenant):
    assert FeatureService.is_feature_active(tenant, "unknown_feature") is False


@pytest.mark.django_db
def test_get_active_features(tenant, other_tenant):
    FeatureService.set_feature(None, "f1", is_active=True)
    FeatureService.set_feature(None, "f2", is_active=True)
    FeatureService.set_feature(tenant, "f2", is_active=False)
    FeatureService.set_feature(tenant, "f3", is_active=True)

    # Global active: f1, f2
    assert set(FeatureService.get_active_features(None)) == {"f1", "f2"}

    # Tenant active: f1 (from global), f3 (from override), f2 is inactive due to override
    assert set(FeatureService.get_active_features(tenant)) == {"f1", "f3"}
