"""Regression tests: every product type exposed by /addbot must be resolvable.

If a product type is offered to users but has no registered catalog, /plan and
/entitlements/check will raise at runtime. These tests catch that gap early.

Add a test case here whenever a new product type is exposed in /addbot.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from cups.api.runtime import app
from cups.service import CUPSService
from cups.storage.sqlite import SQLiteStore
from cups.domain.project import ProductType


# Product types currently offered in apps/cups-bot/handlers/addbot.py
# Keep this list in sync with _PRODUCT_CHOICES in that file.
OFFERED_PRODUCT_TYPES = [
    ProductType.TITAN_FRAMEWORK,
]


@pytest.fixture(autouse=True)
def isolated_service(monkeypatch):
    import cups.api.runtime as runtime_module
    store = SQLiteStore(db_path=":memory:")
    service = CUPSService(store=store)
    monkeypatch.setattr(runtime_module, "_service", service)
    return service


@pytest.fixture
def client():
    return TestClient(app)


@pytest.mark.parametrize("product_type", OFFERED_PRODUCT_TYPES)
class TestOfferedProductTypesAreFullyResolvable:
    """
    For every product type /addbot exposes, the full runtime path must work:
      register project → check entitlement → get plan
    """

    def test_register_and_check_entitlement(self, client, isolated_service, product_type):
        """Registering a project and checking an entitlement must not raise."""
        isolated_service.get_or_create_account(account_id=1)
        project = isolated_service.register_project(
            owner_id=1,
            product=product_type,
            name="TestProject",
        )
        project_id = str(project.project_id)

        # Entitlement check must return a valid response — not a 500
        resp = client.post("/entitlements/check", json={
            "account_id": 1,
            "project_id": project_id,
            "entitlement": _first_entitlement_for(product_type),
        })
        assert resp.status_code == 200, (
            f"Product type {product_type.value!r} has no registered catalog. "
            f"Either add a catalog in src/cups/catalog/ or remove it from /addbot."
        )
        data = resp.json()
        assert "granted" in data
        assert "value" in data

    def test_get_resolved_entitlements_does_not_raise(self, isolated_service, product_type):
        """get_resolved_entitlements must succeed for every offered product type."""
        isolated_service.get_or_create_account(account_id=2)
        isolated_service.register_project(
            owner_id=2,
            product=product_type,
            name="EntitlementTest",
        )
        # Must not raise ValueError("No catalog registered...")
        resolved = isolated_service.get_resolved_entitlements(2, product_type.value)
        assert isinstance(resolved, dict)
        assert len(resolved) > 0

    def test_starter_subscription_created_on_registration(self, isolated_service, product_type):
        """Registering a project must auto-create a Starter subscription."""
        isolated_service.get_or_create_account(account_id=3)
        isolated_service.register_project(
            owner_id=3,
            product=product_type,
            name="SubTest",
        )
        sub = isolated_service.get_subscription(3, product_type.value)
        assert sub is not None
        assert sub.plan.value == "starter"
        assert sub.status.value == "active"


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _first_entitlement_for(product_type: ProductType) -> str:
    """Return the first known entitlement key for a product type."""
    _known: dict[ProductType, str] = {
        ProductType.TITAN_FRAMEWORK: "atlas_access",
    }
    key = _known.get(product_type)
    if key is None:
        pytest.fail(
            f"No known entitlement defined for {product_type.value!r} in test helper. "
            "Update _known in test_product_coverage.py."
        )
    return key
