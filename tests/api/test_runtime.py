"""Integration tests for CUPS Runtime API.

Uses FastAPI TestClient + in-memory SQLite for full isolation.
These tests verify the Acceptance Scenarios at the HTTP level.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from cups.api.runtime import app, _service
from cups.service import CUPSService
from cups.storage.sqlite import SQLiteStore
from cups.domain.project import ProductType


@pytest.fixture(autouse=True)
def isolated_service(monkeypatch):
    """Replace the module-level service with an in-memory one for each test."""
    import cups.api.runtime as runtime_module
    fresh_store = SQLiteStore(db_path=":memory:")
    fresh_service = CUPSService(store=fresh_store)
    monkeypatch.setattr(runtime_module, "_service", fresh_service)
    return fresh_service


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def registered(isolated_service):
    """A pre-registered account + project, returning (account_id, project_id_str)."""
    isolated_service.get_or_create_account(account_id=100)
    project = isolated_service.register_project(
        owner_id=100,
        product=ProductType.TITAN_FRAMEWORK,
        name="TestBot",
    )
    return 100, str(project.project_id)


# ─── Health check ─────────────────────────────────────────────────────────────

def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ─── Starter Entitlements (Phase 1 core scenario) ────────────────────────────

class TestStarterEntitlements:
    def test_atlas_access_false_for_starter(self, client, registered):
        account_id, project_id = registered
        resp = client.post("/entitlements/check", json={
            "account_id": account_id,
            "project_id": project_id,
            "entitlement": "atlas_access",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["granted"] is False
        assert data["value"] is False

    def test_inspector_level_basic_for_starter(self, client, registered):
        account_id, project_id = registered
        resp = client.post("/entitlements/check", json={
            "account_id": account_id,
            "project_id": project_id,
            "entitlement": "inspector_level",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["granted"] is True    # "basic" != "none"
        assert data["value"] == "basic"

    def test_max_projects_starter(self, client, registered):
        account_id, project_id = registered
        resp = client.post("/entitlements/check", json={
            "account_id": account_id,
            "project_id": project_id,
            "entitlement": "max_projects_total",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["granted"] is True   # 3 > 0
        assert data["value"] == 3

    def test_team_access_false_for_starter(self, client, registered):
        account_id, project_id = registered
        resp = client.post("/entitlements/check", json={
            "account_id": account_id,
            "project_id": project_id,
            "entitlement": "team_access",
        })
        assert resp.status_code == 200
        assert resp.json()["granted"] is False


# ─── Response never contains plan or subscription ────────────────────────────

class TestRuntimeIsolation:
    def test_response_has_no_plan_field(self, client, registered):
        account_id, project_id = registered
        resp = client.post("/entitlements/check", json={
            "account_id": account_id,
            "project_id": project_id,
            "entitlement": "atlas_access",
        })
        data = resp.json()
        assert "plan" not in data
        assert "subscription" not in data
        assert "status" not in data


# ─── Error cases ─────────────────────────────────────────────────────────────

class TestErrorCases:
    def test_unknown_project_returns_404(self, client):
        import uuid
        resp = client.post("/entitlements/check", json={
            "account_id": 1,
            "project_id": str(uuid.uuid4()),
            "entitlement": "atlas_access",
        })
        assert resp.status_code == 404

    def test_invalid_project_id_format_returns_422(self, client):
        resp = client.post("/entitlements/check", json={
            "account_id": 1,
            "project_id": "not-a-uuid",
            "entitlement": "atlas_access",
        })
        assert resp.status_code == 422

    def test_unknown_entitlement_returns_404(self, client, registered):
        account_id, project_id = registered
        resp = client.post("/entitlements/check", json={
            "account_id": account_id,
            "project_id": project_id,
            "entitlement": "does_not_exist",
        })
        assert resp.status_code == 404

    def test_wrong_account_returns_403(self, client, registered):
        _, project_id = registered
        resp = client.post("/entitlements/check", json={
            "account_id": 999,   # not the owner
            "project_id": project_id,
            "entitlement": "atlas_access",
        })
        assert resp.status_code == 403
