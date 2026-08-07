"""Contract tests for the direct Referral/Commission vertical slice.

Referral is a commercial layer above subscriptions. It must use successful
simulated payments as the eligibility source while remaining invisible to
Entitlement Resolution, Runtime, and Titan.
"""

from __future__ import annotations

import inspect
from datetime import datetime

import pytest

from cups.api import runtime
from cups.domain.project import ProductType
from cups.domain.referral import CommissionStatus, ReferralProgramConfig
from cups.domain.subscription import PlanName, SubscriptionStatus
from cups.service import CUPSService
from cups.storage.sqlite import SQLiteStore
from apps.titan_framework.cups_client import TitanEntitlementClient


@pytest.fixture
def service() -> CUPSService:
    return CUPSService(
        store=SQLiteStore(db_path=":memory:"),
        referral_config=ReferralProgramConfig(
            commission_rate_bps=2_500,
            commission_window_months=6,
        ),
    )


@pytest.fixture
def referral_pair(service: CUPSService) -> tuple[str, str]:
    """Create referrer A and referred user B with a paid-product subscription."""
    service.get_or_create_account(1)
    service.register_project(
        owner_id=2,
        product=ProductType.TITAN_FRAMEWORK,
        name="ReferredProject",
    )
    service.set_subscription_for_test(
        account_id=2,
        product=ProductType.TITAN_FRAMEWORK,
        plan=PlanName.PLUS,
        status=SubscriptionStatus.ACTIVE,
    )
    referral = service.create_referral_code(1, code="WAHEED25")
    attribution = service.attribute_referral(referral.code, 2)
    return referral.code, attribution.attribution_id


def test_code_and_account_level_attribution_are_created(service: CUPSService):
    service.get_or_create_account(10)
    service.get_or_create_account(20)

    referral = service.create_referral_code(10, code="DIRECT10")
    attribution = service.attribute_referral("DIRECT10", 20)

    assert referral.owner_account_id == 10
    assert attribution.referrer_account_id == 10
    assert attribution.referred_account_id == 20
    assert attribution.referral_code == "DIRECT10"


def test_self_referral_and_duplicate_attribution_are_rejected(
    service: CUPSService,
):
    service.get_or_create_account(10)
    service.get_or_create_account(20)
    service.create_referral_code(10, code="DIRECT10")

    with pytest.raises(ValueError, match="cannot refer themselves"):
        service.attribute_referral("DIRECT10", 10)

    service.attribute_referral("DIRECT10", 20)
    service.get_or_create_account(30)
    service.create_referral_code(30, code="DIRECT30")
    with pytest.raises(ValueError, match="already attributed"):
        service.attribute_referral("DIRECT30", 20)


def test_registration_and_trial_do_not_create_commissions(
    service: CUPSService,
    referral_pair: tuple[str, str],
):
    _, _ = referral_pair

    assert service.get_commissions(1) == []

    subscription = service.get_subscription(
        account_id=2,
        product=ProductType.TITAN_FRAMEWORK.value,
    )
    assert subscription is not None
    service.set_subscription_for_test(
        account_id=2,
        product=ProductType.TITAN_FRAMEWORK,
        plan=subscription.plan,
        status=SubscriptionStatus.TRIAL,
    )
    service.simulate_paid_payment(
        account_id=2,
        product=ProductType.TITAN_FRAMEWORK,
        payment_id="trial-payment",
        amount_minor=499,
        paid_at=datetime(2026, 8, 1),
    )

    assert service.get_commissions(1) == []


def test_starter_subscription_does_not_create_a_paid_commission(
    service: CUPSService,
):
    service.get_or_create_account(1)
    service.register_project(
        owner_id=2,
        product=ProductType.TITAN_FRAMEWORK,
        name="FreeReferredProject",
    )
    service.create_referral_code(1, code="STARTERREF")
    service.attribute_referral("STARTERREF", 2)

    service.simulate_paid_payment(
        account_id=2,
        product=ProductType.TITAN_FRAMEWORK,
        payment_id="starter-payment",
        amount_minor=499,
        paid_at=datetime(2026, 8, 1),
    )

    assert service.get_commissions(1) == []


def test_successful_payment_creates_recurring_commissions(
    service: CUPSService,
    referral_pair: tuple[str, str],
):
    _, _ = referral_pair

    first = service.simulate_paid_payment(
        account_id=2,
        product=ProductType.TITAN_FRAMEWORK,
        payment_id="payment-1",
        amount_minor=499,
        paid_at=datetime(2026, 8, 1),
    )
    second = service.simulate_paid_payment(
        account_id=2,
        product=ProductType.TITAN_FRAMEWORK,
        payment_id="payment-2",
        amount_minor=799,
        paid_at=datetime(2026, 9, 1),
    )

    commissions = service.get_commissions(1)
    assert first.status.value == "succeeded"
    assert second.status.value == "succeeded"
    assert len(commissions) == 2
    assert [commission.commission_amount_minor for commission in commissions] == [
        124,
        199,
    ]
    assert all(
        commission.status is CommissionStatus.APPROVED
        for commission in commissions
    )


def test_payment_id_is_idempotent(service: CUPSService, referral_pair):
    service.simulate_paid_payment(
        account_id=2,
        product=ProductType.TITAN_FRAMEWORK,
        payment_id="same-payment",
        amount_minor=499,
        paid_at=datetime(2026, 8, 1),
    )
    service.simulate_paid_payment(
        account_id=2,
        product=ProductType.TITAN_FRAMEWORK,
        payment_id="same-payment",
        amount_minor=499,
        paid_at=datetime(2026, 8, 1),
    )

    assert len(service.get_commissions(1)) == 1


@pytest.mark.parametrize(
    "status",
    [
        SubscriptionStatus.FROZEN,
        SubscriptionStatus.EXPIRED,
    ],
)
def test_frozen_or_expired_subscriptions_are_not_eligible(
    service: CUPSService,
    referral_pair,
    status: SubscriptionStatus,
):
    subscription = service.get_subscription(
        account_id=2,
        product=ProductType.TITAN_FRAMEWORK.value,
    )
    assert subscription is not None
    service.set_subscription_for_test(
        account_id=2,
        product=ProductType.TITAN_FRAMEWORK,
        plan=subscription.plan,
        status=status,
    )
    service.simulate_paid_payment(
        account_id=2,
        product=ProductType.TITAN_FRAMEWORK,
        payment_id=f"{status.value}-payment",
        amount_minor=499,
        paid_at=datetime(2026, 8, 1),
    )

    assert service.get_commissions(1) == []


def test_commission_window_does_not_restart_after_reactivation(
    service: CUPSService,
    referral_pair,
):
    service.simulate_paid_payment(
        account_id=2,
        product=ProductType.TITAN_FRAMEWORK,
        payment_id="window-start",
        amount_minor=499,
        paid_at=datetime(2026, 1, 31),
    )
    service.simulate_paid_payment(
        account_id=2,
        product=ProductType.TITAN_FRAMEWORK,
        payment_id="inside-window",
        amount_minor=499,
        paid_at=datetime(2026, 7, 30),
    )
    service.simulate_paid_payment(
        account_id=2,
        product=ProductType.TITAN_FRAMEWORK,
        payment_id="outside-window",
        amount_minor=499,
        paid_at=datetime(2026, 8, 1),
    )

    assert len(service.get_commissions(1)) == 2


def test_upgrade_and_downgrade_do_not_restart_commission_window(
    service: CUPSService,
    referral_pair,
):
    service.simulate_paid_payment(
        account_id=2,
        product=ProductType.TITAN_FRAMEWORK,
        payment_id="upgrade-window-start",
        amount_minor=499,
        paid_at=datetime(2026, 1, 1),
    )
    service.set_subscription_for_test(
        account_id=2,
        product=ProductType.TITAN_FRAMEWORK,
        plan=PlanName.CORE,
        status=SubscriptionStatus.ACTIVE,
    )
    service.simulate_paid_payment(
        account_id=2,
        product=ProductType.TITAN_FRAMEWORK,
        payment_id="upgrade-payment",
        amount_minor=799,
        paid_at=datetime(2026, 5, 1),
    )
    service.set_subscription_for_test(
        account_id=2,
        product=ProductType.TITAN_FRAMEWORK,
        plan=PlanName.PLUS,
        status=SubscriptionStatus.ACTIVE,
    )
    service.simulate_paid_payment(
        account_id=2,
        product=ProductType.TITAN_FRAMEWORK,
        payment_id="downgrade-outside-window",
        amount_minor=499,
        paid_at=datetime(2026, 7, 2),
    )

    assert len(service.get_commissions(1)) == 2


def test_refund_reverses_the_related_commission_idempotently(
    service: CUPSService,
    referral_pair,
):
    service.simulate_paid_payment(
        account_id=2,
        product=ProductType.TITAN_FRAMEWORK,
        payment_id="refundable",
        amount_minor=499,
        paid_at=datetime(2026, 8, 1),
    )

    service.simulate_refund("refundable")
    service.simulate_refund("refundable")

    commissions = service.get_commissions(1)
    assert len(commissions) == 1
    assert commissions[0].status is CommissionStatus.REVERSED


def test_referral_is_one_level_only(service: CUPSService):
    service.get_or_create_account(1)
    service.register_project(
        owner_id=2,
        product=ProductType.TITAN_FRAMEWORK,
        name="ReferredProject",
    )
    service.register_project(
        owner_id=3,
        product=ProductType.TITAN_FRAMEWORK,
        name="SecondLevelProject",
    )
    service.set_subscription_for_test(
        account_id=2,
        product=ProductType.TITAN_FRAMEWORK,
        plan=PlanName.PLUS,
        status=SubscriptionStatus.ACTIVE,
    )
    service.set_subscription_for_test(
        account_id=3,
        product=ProductType.TITAN_FRAMEWORK,
        plan=PlanName.PLUS,
        status=SubscriptionStatus.ACTIVE,
    )
    service.create_referral_code(1, code="LEVEL1")
    service.create_referral_code(2, code="LEVEL2")
    service.attribute_referral("LEVEL1", 2)
    service.attribute_referral("LEVEL2", 3)

    service.simulate_paid_payment(
        account_id=3,
        product=ProductType.TITAN_FRAMEWORK,
        payment_id="second-level-payment",
        amount_minor=499,
        paid_at=datetime(2026, 8, 1),
    )

    assert service.get_commissions(1) == []
    assert len(service.get_commissions(2)) == 1


def test_referral_does_not_change_runtime_titan_or_resolution_boundaries(
    service: CUPSService,
    referral_pair,
):
    before = service.get_resolved_entitlements(
        account_id=2,
        product=ProductType.TITAN_FRAMEWORK.value,
    )
    service.simulate_paid_payment(
        account_id=2,
        product=ProductType.TITAN_FRAMEWORK,
        payment_id="boundary-payment",
        amount_minor=499,
        paid_at=datetime(2026, 8, 1),
    )
    after = service.get_resolved_entitlements(
        account_id=2,
        product=ProductType.TITAN_FRAMEWORK.value,
    )

    assert after == before
    assert "Referral" not in inspect.getsource(runtime)
    assert "Commission" not in inspect.getsource(runtime)
    assert "Referral" not in inspect.getsource(TitanEntitlementClient)
    assert "Commission" not in inspect.getsource(TitanEntitlementClient)