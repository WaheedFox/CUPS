"""CUPS — Unified Subscription Platform.

Public surface for Phase 1:
    CUPSService   — all platform operations
    ProductType   — supported product types
    PlanName      — plan identifiers
    ResolvedEntitlements — what Runtime consumes

The Runtime API (FastAPI) lives in cups.api.runtime.
"""

from .service import CUPSService
from .domain.project import ProductType
from .domain.subscription import PlanName
from .domain.entitlement import ResolvedEntitlements, EntitlementValue

__all__ = [
    "CUPSService",
    "ProductType",
    "PlanName",
    "ResolvedEntitlements",
    "EntitlementValue",
]
