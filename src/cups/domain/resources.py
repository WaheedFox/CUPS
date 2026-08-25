"""Resource quota, reservation, and consumption domain values."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class Quota:
    account_id: int
    project_id: UUID
    resource_key: str
    limit: int | None
    used: int
    reserved: int
    remaining: int | None


@dataclass(frozen=True)
class Reservation:
    reservation_id: str
    account_id: int
    project_id: UUID
    resource_key: str
    quantity: int
    status: str
    expires_at: datetime
    idempotency_key: str


@dataclass(frozen=True)
class Consumption:
    consumption_id: str
    usage_record_id: str
    account_id: int
    project_id: UUID
    resource_key: str
    quantity: int
    reservation_id: str | None
    source_event_id: str
    idempotency_key: str
    occurred_at: datetime
    committed_at: datetime
    remaining: int | None
    already_committed: bool = False