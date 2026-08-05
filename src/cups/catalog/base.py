"""ProductCatalog — the base contract every product catalog must fulfill.

Each product defines its own Entitlements independently.
Adding a new product means adding a new catalog file and registering it.
No changes to PHILOSOPHY, DOMAIN, or ARCHITECTURE.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..domain.entitlement import ResolvedEntitlements
from ..domain.subscription import PlanName


class ProductCatalog(ABC):
    """Defines the Entitlement values for each Plan in a specific Product.

    Catalogs are static definitions — they don't evaluate runtime state.
    The EntitlementEngine uses them during Resolution.
    """

    @property
    @abstractmethod
    def product(self) -> str:
        """Product identifier matching ProductType.value (e.g. 'titan-framework')."""

    @abstractmethod
    def resolve(self, plan: PlanName) -> ResolvedEntitlements:
        """Return a fresh copy of Entitlement values for the given Plan."""
