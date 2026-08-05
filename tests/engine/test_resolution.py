"""Tests for Entitlement Resolution Engine.

Tests mirror the ACCEPTANCE-SCENARIOS.md cases exactly.
If a test here fails, the system violated its documented behaviour.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from cups.catalog.titan_framework import TitanFrameworkCatalog
from cups.catalog.cups_bot import CupsBotCatalog
from cups.domain.project import ProductType
from cups.domain.subscription import PlanName, Subscription, SubscriptionStatus
from cups.engine.resolution import EntitlementEngine


@pytest.fixture
def engine() -> EntitlementEngine:
    return EntitlementEngine([TitanFrameworkCatalog(), CupsBotCatalog()])


def _sub(plan: PlanName, status: SubscriptionStatus, product: str = "titan-framework") -> Subscription:
    return Subscription(
        subscription_id=str(uuid4()),
        account_id=1,
        product=product,
        plan=plan,
        status=status,
    )


# ─── Plan Upgrade Scenarios (ACCEPTANCE-SCENARIOS §1) ────────────────────────

class TestUpgradeScenarios:
    def test_starter_to_plus(self, engine):
        """Acceptance: Starter → Plus — atlas_access becomes true, team_access stays false."""
        sub = _sub(PlanName.PLUS, SubscriptionStatus.ACTIVE)
        resolved = engine.resolve(sub)

        assert resolved["atlas_access"] is True
        assert resolved["inspector_level"] == "advanced"
        assert resolved["max_projects_total"] == 10
        assert resolved["team_access"] is False   # Core+ only
        # Runtime never sees plan name — only Entitlements
        assert "plan" not in resolved

    def test_plus_to_core(self, engine):
        """Acceptance: Plus → Core — team_access and runtime_visibility open."""
        sub = _sub(PlanName.CORE, SubscriptionStatus.ACTIVE)
        resolved = engine.resolve(sub)

        assert resolved["team_access"] is True
        assert resolved["runtime_visibility"] is True
        assert resolved["atlas_access"] is True    # inherited
        assert resolved["usage_insights"] is False  # Ultra only

    def test_core_to_ultra(self, engine):
        """Acceptance: Core → Ultra — usage_insights opens."""
        sub = _sub(PlanName.ULTRA, SubscriptionStatus.ACTIVE)
        resolved = engine.resolve(sub)

        assert resolved["usage_insights"] is True
        assert resolved["atlas_access"] is True
        assert resolved["team_access"] is True
        assert resolved["max_projects_total"] == 100
        assert "plan" not in resolved


# ─── Downgrade Scenarios (ACCEPTANCE-SCENARIOS §2) ───────────────────────────

class TestDowngradeScenarios:
    def test_ultra_to_core(self, engine):
        sub = _sub(PlanName.CORE, SubscriptionStatus.ACTIVE)
        resolved = engine.resolve(sub)

        assert resolved["usage_insights"] is False   # Ultra only, now off
        assert resolved["atlas_access"] is True       # still on
        assert resolved["team_access"] is True        # Core keeps it

    def test_core_to_plus(self, engine):
        sub = _sub(PlanName.PLUS, SubscriptionStatus.ACTIVE)
        resolved = engine.resolve(sub)

        assert resolved["team_access"] is False       # was True in Core, now off
        assert resolved["atlas_access"] is True       # still on


# ─── Trial Scenarios (ACCEPTANCE-SCENARIOS §3) ───────────────────────────────

class TestTrialScenarios:
    def test_active_trial_gets_full_plan_entitlements(self, engine):
        """Acceptance: trial status → full plan Entitlements, not Starter."""
        sub = _sub(PlanName.PLUS, SubscriptionStatus.TRIAL)
        resolved = engine.resolve(sub)

        assert resolved["atlas_access"] is True      # Plus entitlement
        # Runtime does NOT see the word "trial" — it sees Entitlements only
        assert "status" not in resolved
        assert "trial_ends_at" not in resolved

    def test_expired_trial_reverts_to_starter(self, engine):
        """Acceptance: frozen status → Starter Entitlements regardless of plan."""
        sub = _sub(PlanName.PLUS, SubscriptionStatus.FROZEN)
        resolved = engine.resolve(sub)

        assert resolved["atlas_access"] is False     # back to Starter
        assert resolved["max_projects_total"] == 3   # Starter limit


# ─── Subscription Lifecycle (ACCEPTANCE-SCENARIOS §4) ────────────────────────

class TestSubscriptionLifecycle:
    def test_grace_keeps_full_entitlements(self, engine):
        """Acceptance: grace period — user still has Core Entitlements."""
        sub = _sub(PlanName.CORE, SubscriptionStatus.GRACE)
        resolved = engine.resolve(sub)

        assert resolved["team_access"] is True        # still active during grace
        assert resolved["atlas_access"] is True

    def test_frozen_reverts_to_starter(self, engine):
        """Acceptance: frozen → Entitlements drop to Starter."""
        sub = _sub(PlanName.CORE, SubscriptionStatus.FROZEN)
        resolved = engine.resolve(sub)

        assert resolved["atlas_access"] is False
        assert resolved["team_access"] is False
        assert resolved["max_projects_total"] == 3

    def test_expired_same_as_frozen(self, engine):
        sub = _sub(PlanName.ULTRA, SubscriptionStatus.EXPIRED)
        resolved = engine.resolve(sub)

        assert resolved["atlas_access"] is False
        assert resolved["usage_insights"] is False
        assert resolved["max_projects_total"] == 3


# ─── Runtime Isolation (ACCEPTANCE-SCENARIOS §5) ─────────────────────────────

class TestRuntimeIsolation:
    def test_resolved_entitlements_never_contain_plan(self, engine):
        """Runtime MUST NEVER see plan name."""
        for plan in PlanName:
            sub = _sub(plan, SubscriptionStatus.ACTIVE)
            resolved = engine.resolve(sub)
            assert "plan" not in resolved
            assert "subscription" not in resolved
            assert "status" not in resolved

    def test_no_subscription_returns_starter(self, engine):
        resolved = engine.resolve_starter("titan-framework")
        assert resolved["atlas_access"] is False
        assert resolved["max_projects_total"] == 3
        assert resolved["inspector_level"] == "basic"

    def test_unknown_product_raises(self, engine):
        with pytest.raises(ValueError, match="No catalog registered"):
            engine.resolve_starter("unknown-product")


# ─── Catalog Completeness ────────────────────────────────────────────────────

class TestCatalogCompleteness:
    def test_active_product_types_have_matching_catalogs(self):
        """Every active product must have a declared and registered catalog."""
        catalogs = [TitanFrameworkCatalog(), CupsBotCatalog()]
        catalog_products = {catalog.product for catalog in catalogs}
        active_product_types = {
            ProductType.TITAN_FRAMEWORK,
            ProductType.CUPS_BOT,
        }

        assert catalog_products == {product.value for product in active_product_types}

    def test_titan_framework_all_plans_have_same_keys(self):
        catalog = TitanFrameworkCatalog()
        keys_per_plan = [set(catalog.resolve(p).keys()) for p in PlanName]
        # All plans must define the same Entitlement keys
        assert len(set(frozenset(k) for k in keys_per_plan)) == 1

    def test_cups_bot_all_plans_have_same_keys(self):
        catalog = CupsBotCatalog()
        keys_per_plan = [set(catalog.resolve(p).keys()) for p in PlanName]
        assert len(set(frozenset(k) for k in keys_per_plan)) == 1

    def test_resolve_returns_fresh_copy(self):
        """Mutating resolved entitlements must not affect the catalog."""
        catalog = TitanFrameworkCatalog()
        r1 = catalog.resolve(PlanName.STARTER)
        r1["atlas_access"] = True   # mutate the copy
        r2 = catalog.resolve(PlanName.STARTER)
        assert r2["atlas_access"] is False  # catalog unchanged
