"""Subscription — the actual relationship between an Account and a Plan.

Lifecycle: trial → active → grace → frozen → expired → (Starter)

Rules:
- trial/active/grace  → plan's full Entitlements apply
- frozen/expired      → Starter Entitlements apply (data preserved)
- No subscription     → Starter Entitlements apply (default)

Runtime MUST NEVER read this directly. It reads ResolvedEntitlements only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class SubscriptionStatus(str, Enum):
    TRIAL = "trial"
    ACTIVE = "active"
    GRACE = "grace"      # payment failed — short grace window
    FROZEN = "frozen"    # paid entitlements frozen, data preserved
    EXPIRED = "expired"  # after frozen period — reverts to Starter


class PlanName(str, Enum):
    """Commercial plan names. Code never checks plan — only Entitlements."""

    STARTER = "starter"
    PLUS = "plus"
    CORE = "core"
    ULTRA = "ultra"


@dataclass
class Subscription:
    """The live contract between an Account and a Plan for a specific Product."""

    subscription_id: str       # UUID string
    account_id: int
    product: str               # ProductType.value
    plan: PlanName
    status: SubscriptionStatus
    period: str = "monthly"    # monthly | annual
    started_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime | None = None
    trial_ends_at: datetime | None = None
