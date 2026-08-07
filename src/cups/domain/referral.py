"""Direct Referral and simulated Commission domain entities.

This module is intentionally separate from Subscription and Entitlement
Resolution. It models commercial attribution only; it is not a billing
provider or a Runtime contract.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


@dataclass(frozen=True)
class ReferralProgramConfig:
    """Configurable simulation settings for the direct referral program."""

    commission_rate_bps: int = 2_500
    commission_window_months: int = 6

    def __post_init__(self) -> None:
        if not 0 <= self.commission_rate_bps <= 10_000:
            raise ValueError("commission_rate_bps must be between 0 and 10000.")
        if self.commission_window_months <= 0:
            raise ValueError("commission_window_months must be positive.")


@dataclass
class ReferralCode:
    code: str
    owner_account_id: int
    created_at: datetime = field(default_factory=datetime.utcnow)
    active: bool = True


@dataclass
class ReferralAttribution:
    attribution_id: str
    referrer_account_id: int
    referred_account_id: int
    referral_code: str
    attributed_at: datetime = field(default_factory=datetime.utcnow)
    first_eligible_payment_at: datetime | None = None


class PaymentStatus(str, Enum):
    SUCCEEDED = "succeeded"
    REFUNDED = "refunded"


@dataclass
class SimulatedPayment:
    payment_id: str
    account_id: int
    product: str
    subscription_id: str
    amount_minor: int
    currency: str = "USD"
    status: PaymentStatus = PaymentStatus.SUCCEEDED
    paid_at: datetime = field(default_factory=datetime.utcnow)
    refunded_at: datetime | None = None


class CommissionStatus(str, Enum):
    APPROVED = "approved"
    REVERSED = "reversed"


@dataclass
class Commission:
    commission_id: str
    attribution_id: str
    payment_id: str
    gross_amount_minor: int
    rate_bps: int
    commission_amount_minor: int
    status: CommissionStatus = CommissionStatus.APPROVED
    created_at: datetime = field(default_factory=datetime.utcnow)
    reversed_at: datetime | None = None