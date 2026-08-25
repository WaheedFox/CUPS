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
from datetime import datetime
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


class QuotaRequest(BaseModel):
    account_id: int
    project_id: str
    resource_key: str


class QuotaResponse(BaseModel):
    resource_key: str
    limit: int | None
    used: int
    reserved: int
    remaining: int | None


class ReservationRequest(BaseModel):
    account_id: int
    project_id: str
    resource_key: str
    quantity: int
    idempotency_key: str
    expires_at: datetime


class ReservationResponse(BaseModel):
    reservation_id: str
    resource_key: str
    quantity: int
    status: str
    expires_at: datetime


class ConsumptionRequest(BaseModel):
    account_id: int
    project_id: str
    resource_key: str
    quantity: int
    reservation_id: str | None = None
    source_event_id: str
    idempotency_key: str
    occurred_at: datetime | None = None


class ConsumptionResponse(BaseModel):
    consumption_id: str
    usage_record_id: str
    resource_key: str
    quantity: int
    reservation_id: str | None
    remaining: int | None
    status: str
    committed_at: datetime


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


def _project_uuid(project_id: str) -> UUID:
    try:
        return UUID(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="project_id must be a valid UUID.") from exc


def _resource_error(exc: ValueError) -> HTTPException:
    codes = {
        "UNKNOWN_RESOURCE": 404,
        "QUOTA_EXCEEDED": 409,
        "RESERVATION_NOT_FOUND": 404,
        "RESERVATION_EXPIRED": 409,
        "CONSUMPTION_EXCEEDS_RESERVATION": 409,
        "IDEMPOTENCY_CONFLICT": 409,
        "INVALID_REQUEST": 422,
        "METER_INVALID": 500,
    }
    code = str(exc)
    return HTTPException(status_code=codes.get(code, 422), detail=code)


@app.post("/v1/runtime/resources/quota", response_model=QuotaResponse)
def quota(req: QuotaRequest) -> QuotaResponse:
    try:
        value = _service.get_quota(req.account_id, _project_uuid(req.project_id), req.resource_key)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise _resource_error(exc) from exc
    return QuotaResponse(
        resource_key=value.resource_key, limit=value.limit, used=value.used,
        reserved=value.reserved, remaining=value.remaining,
    )


@app.post("/v1/runtime/resources/reserve", response_model=ReservationResponse)
def reserve(req: ReservationRequest) -> ReservationResponse:
    try:
        value = _service.reserve_resource(
            req.account_id, _project_uuid(req.project_id), req.resource_key,
            req.quantity, req.idempotency_key, req.expires_at,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise _resource_error(exc) from exc
    return ReservationResponse(
        reservation_id=value.reservation_id, resource_key=value.resource_key,
        quantity=value.quantity, status=value.status, expires_at=value.expires_at,
    )


@app.post("/v1/runtime/resources/consume", response_model=ConsumptionResponse)
def consume(req: ConsumptionRequest) -> ConsumptionResponse:
    try:
        value = _service.record_consumption(
            req.account_id, _project_uuid(req.project_id), req.resource_key,
            req.quantity, req.reservation_id, req.source_event_id,
            req.idempotency_key, req.occurred_at,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise _resource_error(exc) from exc
    return ConsumptionResponse(
        consumption_id=value.consumption_id, usage_record_id=value.usage_record_id,
        resource_key=value.resource_key, quantity=value.quantity,
        reservation_id=value.reservation_id, remaining=value.remaining,
        status="already_committed" if value.already_committed else "committed",
        committed_at=value.committed_at,
    )


@app.get("/health", summary="Health check.")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "cups-runtime-api", "version": "0.1.0"}
