"""Entitlement catalog for the cups-bot product.

Source of truth: docs/services/cups-bot/ENTITLEMENTS.md

CUPS Bot checks Entitlements through the same mechanism as any other product.
No exception for the internal bot — this is dogfooding by design.
"""

from __future__ import annotations

from ..domain.entitlement import ResolvedEntitlements
from ..domain.subscription import PlanName
from .base import ProductCatalog

_PLANS: dict[PlanName, ResolvedEntitlements] = {
    PlanName.STARTER: {
        "cups_account_view": True,     # always — user must see what they paid for
        "cups_projects_view": True,    # always — same reason
        "cups_team_management": False,
        "cups_billing_history": False,
        "cups_usage_reports": False,
        "cups_project_transfer": False,
    },
    PlanName.PLUS: {
        "cups_account_view": True,
        "cups_projects_view": True,
        "cups_team_management": False,
        "cups_billing_history": True,
        "cups_usage_reports": False,
        "cups_project_transfer": False,
    },
    PlanName.CORE: {
        "cups_account_view": True,
        "cups_projects_view": True,
        "cups_team_management": True,
        "cups_billing_history": True,
        "cups_usage_reports": False,
        "cups_project_transfer": True,
    },
    PlanName.ULTRA: {
        "cups_account_view": True,
        "cups_projects_view": True,
        "cups_team_management": True,
        "cups_billing_history": True,
        "cups_usage_reports": True,
        "cups_project_transfer": True,
    },
}


class CupsBotCatalog(ProductCatalog):
    @property
    def product(self) -> str:
        return "cups-bot"

    def resolve(self, plan: PlanName) -> ResolvedEntitlements:
        return dict(_PLANS[plan])
