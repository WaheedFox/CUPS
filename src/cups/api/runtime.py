"""CUPS Runtime API — the single endpoint that Runtime consumers call.

POST /entitlements/check
  → { granted: bool, value: bool | int | str | null }

This endpoint NEVER exposes plan names, subscription status, or billing state.
It exposes only Resolved Entitlements. This enforces the foundational rule:

    Runtime MUST NEVER evaluate subscriptions directly.
    Runtime MUST consume resolved entitlements only.
"""

from __future__ import annotations

import os
from uuid import UUID

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

from ..service import CUPSService, _compute_granted
from ..domain.entitlement import EntitlementValue

# One shared service instance for the API process
_service = CUPSService(store=None)  # uses default cups.db

app = FastAPI(
    title="CUPS Runtime API",
    description="Entitlement checks for registered CUPS projects.",
    version="0.1.0",
)


# ─── Request / Response models ────────────────────────────────────────────────

class EntitlementCheckRequest(BaseModel):
    account_id: int
    project_id: str   # UUID string — validated below
    entitlement: str


class EntitlementCheckResponse(BaseModel):
    granted: bool
    value: EntitlementValue | None = None


# ─── Endpoints ────────────────────────────────────────────────────────────────

@app.post(
    "/entitlements/check",
    response_model=EntitlementCheckResponse,
    summary="Check a single Entitlement for an account+project pair.",
)
def check_entitlement(req: EntitlementCheckRequest) -> EntitlementCheckResponse:
    """Check whether an account holds a specific Entitlement.

    The response never includes plan name or subscription status — by design.
    Callers receive only `granted` and `value`.
    """
    try:
        project_id = UUID(req.project_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="project_id must be a valid UUID.",
        )

    project = _service.get_project(project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        )

    # Phase 1: owner-only access. Team members supported in Phase 4.
    if project.owner_id != req.account_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account does not own this project.",
        )

    try:
        granted, value = _service.check_entitlement(
            req.account_id, project_id, req.entitlement
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    return EntitlementCheckResponse(granted=granted, value=value)


@app.get("/health", summary="Health check.")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "cups-runtime-api", "version": "0.1.0"}
