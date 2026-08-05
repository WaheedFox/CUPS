"""Minimal Titan consumer client for the CUPS Runtime API."""

from __future__ import annotations


class TitanEntitlementClient:
    """Titan's Runtime-only entitlement checks."""

    def __init__(self, runtime, account_id: int, project_id: str) -> None:
        self._runtime = runtime
        self._account_id = account_id
        self._project_id = project_id

    def require(self, entitlement: str) -> bool:
        return bool(self._check(entitlement)["granted"])

    def value(self, entitlement: str):
        return self._check(entitlement)["value"]

    def tier(self, entitlement: str) -> str:
        return str(self.value(entitlement))

    def _check(self, entitlement: str) -> dict:
        response = self._runtime.post(
            "/entitlements/check",
            json={
                "account_id": self._account_id,
                "project_id": self._project_id,
                "entitlement": entitlement,
            },
        )
        response.raise_for_status()
        return response.json()