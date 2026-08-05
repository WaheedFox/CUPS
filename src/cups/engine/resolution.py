"""Entitlement Resolution — the core domain process of CUPS.

This is NOT a mere utility. It is the process that enforces the fundamental rule:

    Runtime MUST NEVER evaluate subscriptions directly.
    Runtime MUST consume resolved entitlements only.

How it works:
  Subscription (account's plan + status)
       ↓  EntitlementEngine.resolve()
  ResolvedEntitlements (what Runtime actually sees)

Status → effective plan mapping:
  trial / active / grace  → use the subscription's plan
  frozen / expired        → downgrade to Starter (data preserved, paid features off)
  no subscription         → Starter (default for all new accounts)
"""

from __future__ import annotations

from ..catalog.base import ProductCatalog
from ..domain.entitlement import EntitlementValue, ResolvedEntitlements
from ..domain.subscription import PlanName, Subscription, SubscriptionStatus

# These statuses keep the paid plan's Entitlements active
_ACTIVE_STATUSES: frozenset[SubscriptionStatus] = frozenset({
    SubscriptionStatus.TRIAL,
    SubscriptionStatus.ACTIVE,
    SubscriptionStatus.GRACE,   # grace: user still has access, paying expected soon
})

# These statuses revert to Starter (paid Entitlements off, data preserved)
_FROZEN_STATUSES: frozenset[SubscriptionStatus] = frozenset({
    SubscriptionStatus.FROZEN,
    SubscriptionStatus.EXPIRED,
})


class EntitlementEngine:
    """Resolves a Subscription into Resolved Entitlements.

    CUPS determines permission. Extensions enforce behavior.
    """

    def __init__(self, catalogs: list[ProductCatalog]) -> None:
        self._catalogs: dict[str, ProductCatalog] = {c.product: c for c in catalogs}

    def resolve(self, subscription: Subscription) -> ResolvedEntitlements:
        """Transform a Subscription into its current Resolved Entitlements.

        The result is what Runtime consumes — it never sees the subscription itself.
        """
        catalog = self._get_catalog(subscription.product)

        if subscription.status in _FROZEN_STATUSES:
            # Paid features off. Data is preserved by policy, not here.
            effective_plan = PlanName.STARTER
        elif subscription.status in _ACTIVE_STATUSES:
            effective_plan = subscription.plan
        else:
            # Unknown status — fail safe to Starter
            effective_plan = PlanName.STARTER

        return catalog.resolve(effective_plan)

    def resolve_starter(self, product: str) -> ResolvedEntitlements:
        """Return Starter Entitlements for a product.

        Used when no Subscription exists (new account, no registration yet).
        Starter is always the default — never an error state.
        """
        return self._get_catalog(product).resolve(PlanName.STARTER)

    def _get_catalog(self, product: str) -> ProductCatalog:
        catalog = self._catalogs.get(product)
        if catalog is None:
            raise ValueError(
                f"No catalog registered for product {product!r}. "
                "Add a ProductCatalog subclass and register it with the engine."
            )
        return catalog

    @property
    def known_products(self) -> list[str]:
        """List of product identifiers this engine can resolve."""
        return list(self._catalogs.keys())
