"""Entitlement catalog for the titan-framework product.

Source of truth: docs/services/titan-framework/ENTITLEMENTS.md
Three Entitlement types: Boolean, Numeric, CapabilityTier.

The library itself (pip install titan-lib) is always free.
CUPS unlocks the surrounding tooling layer.
"""

from __future__ import annotations

from ..domain.entitlement import ResolvedEntitlements
from ..domain.subscription import PlanName
from .base import ProductCatalog

# Entitlement values per plan — authoritative, manually maintained.
# Never modify these without a corresponding update to
# docs/services/titan-framework/ENTITLEMENTS.md
_PLANS: dict[PlanName, ResolvedEntitlements] = {
    PlanName.STARTER: {
        # Quantitative limits
        "max_projects_total": 3,
        "team_members_limit": 0,
        # Developer Workflow
        "atlas_access": False,
        "lint_advanced": False,
        "inspector_level": "basic",   # basic state only, no history
        "playground_access": False,
        "profiler_access": False,
        "timeline_access": False,
        # Production Workflow
        "runtime_visibility": False,
        "usage_insights": False,
        # Team
        "team_access": False,
    },
    PlanName.PLUS: {
        "max_projects_total": 10,
        "team_members_limit": 0,
        "atlas_access": True,
        "lint_advanced": True,
        "inspector_level": "advanced",
        "playground_access": True,
        "profiler_access": True,
        "timeline_access": True,
        "runtime_visibility": False,
        "usage_insights": False,
        "team_access": False,
    },
    PlanName.CORE: {
        "max_projects_total": 20,
        "team_members_limit": 5,
        "atlas_access": True,
        "lint_advanced": True,
        "inspector_level": "advanced",
        "playground_access": True,
        "profiler_access": True,
        "timeline_access": True,
        "runtime_visibility": True,
        "usage_insights": False,
        "team_access": True,
    },
    PlanName.ULTRA: {
        "max_projects_total": 100,
        "team_members_limit": 20,
        "atlas_access": True,
        "lint_advanced": True,
        "inspector_level": "advanced",
        "playground_access": True,
        "profiler_access": True,
        "timeline_access": True,
        "runtime_visibility": True,
        "usage_insights": True,
        "team_access": True,
    },
}


class TitanFrameworkCatalog(ProductCatalog):
    @property
    def product(self) -> str:
        return "titan-framework"

    def resolve(self, plan: PlanName) -> ResolvedEntitlements:
        return dict(_PLANS[plan])
