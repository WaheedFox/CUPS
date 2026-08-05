"""CUPSService — high-level operations for CUPS Platform.

This is the primary interface for both the Runtime API and CUPS Bot.
It wires together storage, engine, and domain logic.

Both consumers (API and Bot) import this — neither touches storage or engine directly.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from .catalog.cups_bot import CupsBotCatalog
from .catalog.titan_framework import TitanFrameworkCatalog
from .domain.account import Account
from .domain.entitlement import EntitlementValue, ResolvedEntitlements
from .domain.project import Project, ProductType
from .domain.subscription import PlanName, Subscription, SubscriptionStatus
from .engine.resolution import EntitlementEngine
from .storage.sqlite import SQLiteStore


class CUPSService:
    """All CUPS Platform operations accessible through a clean interface.

    One instance per process. Shared between the API and any other consumer.
    """

    def __init__(self, store: SQLiteStore | None = None) -> None:
        self._store = store or SQLiteStore()
        self._engine = EntitlementEngine([
            TitanFrameworkCatalog(),
            CupsBotCatalog(),
        ])

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
