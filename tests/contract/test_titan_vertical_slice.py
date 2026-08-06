"""Contract tests for the Phase 2 Titan vertical slice.

These tests describe the boundary before implementing it:

    internal test state change → CUPS Runtime → Titan behavior

The Titan-side client is intentionally tested through Runtime only. It must
not import or inspect CUPS Subscription or Plan models.
"""

from __future__ import annotations

import inspect

import pytest
from fastapi.testclient import TestClient

from cups.api.runtime import app
from cups.domain.project import ProductType
from cups.domain.subscription import PlanName, SubscriptionStatus
from cups.service import CUPSService
from cups.storage.sqlite import SQLiteStore
from apps.titan_framework.cups_client import TitanEntitlementClient


@pytest.fixture
def service(monkeypatch):
    import cups.api.runtime as runtime_module

    store = SQLiteStore(db_path=":memory:")
    service = CUPSService(store=store)
    monkeypatch.setattr(runtime_module, "_service", service)
    return service


@pytest.fixture
def registered(service):
    account_id = 100
    project = service.register_project(
        owner_id=account_id,
        product=ProductType.TITAN_FRAMEWORK,
        name="VerticalSliceBot",
    )
    return account_id, str(project.project_id)


@pytest.fixture
def titan(service, registered):
    account_id, project_id = registered
    return TitanEntitlementClient(
        runtime=TestClient(app),
        account_id=account_id,
        project_id=project_id,
    )


def test_starter_closes_atlas_access(titan):
    assert titan.require("atlas_access") is False
    assert titan.tier("inspector_level") == "basic"


def test_paid_plan_opens_feature_and_exposes_tier(titan, service, registered):
    account_id, project_id = registered

    service.set_subscription_for_test(
        account_id=account_id,
        product=ProductType.TITAN_FRAMEWORK,
        plan=PlanName.PLUS,
        status=SubscriptionStatus.ACTIVE,
    )

    assert titan.require("atlas_access") is True
    assert titan.tier("inspector_level") == "advanced"


@pytest.mark.parametrize(
    "status",
    [SubscriptionStatus.FROZEN, SubscriptionStatus.EXPIRED],
)
def test_frozen_or_expired_closes_paid_feature(titan, service, registered, status):
    account_id, project_id = registered

    service.set_subscription_for_test(
        account_id=account_id,
        product=ProductType.TITAN_FRAMEWORK,
        plan=PlanName.PLUS,
        status=status,
    )

    assert titan.require("atlas_access") is False
    assert titan.tier("inspector_level") == "basic"


def test_titan_client_has_no_subscription_or_plan_dependency():
    source = inspect.getsource(TitanEntitlementClient)

    assert "Subscription" not in source
    assert "PlanName" not in source
    assert "cups.domain.subscription" not in source