"""CUPSService — high-level operations for CUPS Platform.

This is the primary interface for both the Runtime API and CUPS Bot.
It wires together storage, engine, and domain logic.

Both consumers (API and Bot) import this — neither touches storage or engine directly.
"""

from __future__ import annotations

import calendar
from datetime import datetime
from uuid import UUID, uuid4

from .catalog.cups_bot import CupsBotCatalog
from .catalog.titan_framework import TitanFrameworkCatalog
from .domain.account import Account
from .domain.entitlement import EntitlementValue, ResolvedEntitlements
from .domain.project import Project, ProductType
from .domain.referral import (
    Commission,
    CommissionStatus,
    PaymentStatus,
    ReferralAttribution,
    ReferralCode,
    ReferralProgramConfig,
    SimulatedPayment,
)
from .domain.subscription import PlanName, Subscription, SubscriptionStatus
from .engine.resolution import EntitlementEngine
from .storage.sqlite import SQLiteStore


class CUPSService:
    """All CUPS Platform operations accessible through a clean interface.

    One instance per process. Shared between the API and any other consumer.
    """

    def __init__(
        self,
        store: SQLiteStore | None = None,
        referral_config: ReferralProgramConfig | None = None,
    ) -> None:
        self._store = store or SQLiteStore()
        self._engine = EntitlementEngine([
            TitanFrameworkCatalog(),
            CupsBotCatalog(),
        ])
        self._referral_config = referral_config or ReferralProgramConfig()

    # ─── Account ─────────────────────────────────────────────────────────────

    def get_or_create_account(
        self, account_id: int, username: str | None = None
    ) -> tuple[Account, bool]:
        """Return (account, created). Creates account on first call for this id."""
        account = self._store.accounts.get(account_id)
        if account is not None:
            return account, False

        account = Account(account_id=account_id, username=username)
        self._store.accounts.create(account)
        return account, True

    def get_account(self, account_id: int) -> Account | None:
        return self._store.accounts.get(account_id)

    # ─── Project ─────────────────────────────────────────────────────────────

    def register_project(
        self, owner_id: int, product: ProductType, name: str
    ) -> Project:
        """Register a project and auto-create a Starter subscription for its product."""
        # Ensure account exists (idempotent)
        self.get_or_create_account(owner_id)

        project = Project(
            project_id=uuid4(),
            owner_id=owner_id,
            product=product,
            name=name,
        )
        self._store.projects.create(project)

        # Create Starter subscription for this product if none exists yet
        existing = self._store.subscriptions.get(owner_id, product.value)
        if existing is None:
            sub = Subscription(
                subscription_id=str(uuid4()),
                account_id=owner_id,
                product=product.value,
                plan=PlanName.STARTER,
                status=SubscriptionStatus.ACTIVE,
            )
            self._store.subscriptions.create(sub)

        return project

    def get_project(self, project_id: UUID) -> Project | None:
        return self._store.projects.get(project_id)

    def get_projects(self, owner_id: int) -> list[Project]:
        return self._store.projects.get_by_owner(owner_id)

    # ─── Entitlement Resolution ───────────────────────────────────────────────

    def get_resolved_entitlements(
        self, account_id: int, product: str
    ) -> ResolvedEntitlements:
        """Return current Resolved Entitlements for an account+product pair.

        Runtime MUST consume only what this method returns.
        Never exposes subscription or plan to callers.
        """
        subscription = self._store.subscriptions.get(account_id, product)
        if subscription is None:
            return self._engine.resolve_starter(product)
        return self._engine.resolve(subscription)

    def check_entitlement(
        self,
        account_id: int,
        project_id: UUID,
        entitlement: str,
    ) -> tuple[bool, EntitlementValue | None]:
        """Check a single Entitlement. Returns (granted, value).

        Raises:
            KeyError  — project not found
            ValueError — unknown entitlement name for this product
        """
        project = self._store.projects.get(project_id)
        if project is None:
            raise KeyError(f"Project {project_id} not found.")

        resolved = self.get_resolved_entitlements(account_id, project.product.value)

        if entitlement not in resolved:
            raise ValueError(
                f"Unknown entitlement {entitlement!r} for product {project.product.value!r}."
            )

        value = resolved[entitlement]
        granted = _compute_granted(value)
        return granted, value

    # ─── Subscription ─────────────────────────────────────────────────────────

    def get_subscription(self, account_id: int, product: str) -> Subscription | None:
        return self._store.subscriptions.get(account_id, product)

    def set_subscription_for_test(
        self,
        account_id: int,
        product: ProductType,
        plan: PlanName,
        status: SubscriptionStatus,
    ) -> None:
        """Internal test-only state change; this is not Billing."""
        subscription = self.get_subscription(account_id, product.value)
        if subscription is None:
            raise KeyError(
                f"No subscription for account {account_id} and product {product.value!r}."
            )

        subscription.plan = plan
        subscription.status = status
        self._store.subscriptions.update(subscription)

    # ─── Referral / simulated commercial operations ──────────────────────────

    def create_referral_code(self, account_id: int, code: str) -> ReferralCode:
        """Create a direct referral code for an existing account.

        This is an internal simulation operation, not a public billing API.
        """
        if self.get_account(account_id) is None:
            raise ValueError(f"Account {account_id} not found.")
        normalized_code = code.strip()
        if not normalized_code:
            raise ValueError("Referral code cannot be empty.")
        if self._store.referral_codes.get(normalized_code) is not None:
            raise ValueError("Referral code already exists.")

        referral_code = ReferralCode(
            code=normalized_code,
            owner_account_id=account_id,
        )
        self._store.referral_codes.create(referral_code)
        return referral_code

    def attribute_referral(
        self, code: str, referred_account_id: int
    ) -> ReferralAttribution:
        """Permanently attribute an existing account to one direct referrer."""
        referral_code = self._store.referral_codes.get(code.strip())
        if referral_code is None or not referral_code.active:
            raise ValueError("Referral code is invalid or inactive.")
        if self.get_account(referred_account_id) is None:
            raise ValueError(f"Account {referred_account_id} not found.")
        if referral_code.owner_account_id == referred_account_id:
            raise ValueError("An account cannot refer themselves.")
        if self._store.referral_attributions.get_by_referred(
            referred_account_id
        ) is not None:
            raise ValueError("Account is already attributed.")

        attribution = ReferralAttribution(
            attribution_id=str(uuid4()),
            referrer_account_id=referral_code.owner_account_id,
            referred_account_id=referred_account_id,
            referral_code=referral_code.code,
        )
        self._store.referral_attributions.create(attribution)
        return attribution

    def simulate_paid_payment(
        self,
        account_id: int,
        product: ProductType | str,
        payment_id: str,
        amount_minor: int,
        paid_at: datetime | None = None,
        currency: str = "USD",
    ) -> SimulatedPayment:
        """Record a successful simulated payment and its eligible commission.

        This deliberately does not mutate Subscription state. A paid
        subscription state is prepared separately by the existing test-only
        subscription operation.
        """
        if amount_minor <= 0:
            raise ValueError("Simulated payment amount must be positive.")
        if not payment_id.strip():
            raise ValueError("Payment id cannot be empty.")
        product_key = product.value if isinstance(product, ProductType) else product
        subscription = self.get_subscription(account_id, product_key)
        if subscription is None:
            raise ValueError("No subscription exists for this account and product.")
        existing_payment = self._store.simulated_payments.get(payment_id)
        if existing_payment is not None:
            return existing_payment

        payment = SimulatedPayment(
            payment_id=payment_id,
            account_id=account_id,
            product=product_key,
            subscription_id=subscription.subscription_id,
            amount_minor=amount_minor,
            currency=currency,
            paid_at=paid_at or datetime.utcnow(),
        )
        self._store.simulated_payments.create(payment)
        self._create_eligible_commission(payment, subscription)
        return payment

    def simulate_refund(self, payment_id: str) -> SimulatedPayment:
        """Refund a simulated payment and reverse its commission, if any."""
        payment = self._store.simulated_payments.get(payment_id)
        if payment is None:
            raise ValueError(f"Payment {payment_id!r} not found.")
        if payment.status is PaymentStatus.REFUNDED:
            return payment

        payment.status = PaymentStatus.REFUNDED
        payment.refunded_at = datetime.utcnow()
        self._store.simulated_payments.update(payment)

        commission = self._store.commissions.get_by_payment(payment_id)
        if commission is not None:
            commission.status = CommissionStatus.REVERSED
            commission.reversed_at = payment.refunded_at
            self._store.commissions.update(commission)
        return payment

    def get_commissions(self, referrer_account_id: int) -> list[Commission]:
        """Return simulated commissions attributed to a referrer."""
        return self._store.commissions.get_by_referrer(referrer_account_id)

    def _create_eligible_commission(
        self, payment: SimulatedPayment, subscription: Subscription
    ) -> Commission | None:
        if subscription.status not in {
            SubscriptionStatus.ACTIVE,
            SubscriptionStatus.GRACE,
        }:
            return None
        if subscription.plan is PlanName.STARTER:
            return None

        attribution = self._store.referral_attributions.get_by_referred(
            payment.account_id
        )
        if attribution is None:
            return None
        if self._store.commissions.get_by_payment(payment.payment_id) is not None:
            return None

        first_payment_at = attribution.first_eligible_payment_at
        if first_payment_at is None:
            attribution.first_eligible_payment_at = payment.paid_at
            self._store.referral_attributions.update(attribution)
            first_payment_at = payment.paid_at

        window_end = _add_months(
            first_payment_at,
            self._referral_config.commission_window_months,
        )
        if payment.paid_at >= window_end:
            return None

        commission = Commission(
            commission_id=str(uuid4()),
            attribution_id=attribution.attribution_id,
            payment_id=payment.payment_id,
            gross_amount_minor=payment.amount_minor,
            rate_bps=self._referral_config.commission_rate_bps,
            commission_amount_minor=(
                payment.amount_minor
                * self._referral_config.commission_rate_bps
                // 10_000
            ),
        )
        self._store.commissions.create(commission)
        return commission

# ─── Helpers ─────────────────────────────────────────────────────────────────

def _compute_granted(value: EntitlementValue) -> bool:
    """Derive the boolean 'granted' flag from an Entitlement value.

    Boolean → value itself
    Numeric → value > 0
    CapabilityTier (str) → value != "none"
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value > 0
    if isinstance(value, str):
        return value != "none"
    return bool(value)


def _add_months(value: datetime, months: int) -> datetime:
    """Add calendar months while preserving a valid day of month."""
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)
