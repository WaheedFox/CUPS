"""Contract tests for the Account → Project → Quota → Usage slice."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

import pytest

from cups.domain.project import ProductType
from cups.domain.subscription import PlanName, SubscriptionStatus
from cups.service import CUPSService
from cups.storage.sqlite import SQLiteStore


@pytest.fixture
def service() -> CUPSService:
    store = SQLiteStore(":memory:")
    yield CUPSService(store=store)
    store.close()


@pytest.fixture
def project(service: CUPSService):
    account_id = 100
    project = service.register_project(
        account_id, ProductType.TITAN_FRAMEWORK, "ResourceSlice"
    )
    return account_id, project.project_id


def test_vertical_slice_starter_quota_reservation_consumption(service, project):
    account_id, project_id = project
    quota = service.get_quota(account_id, project_id, "projects")
    assert (quota.limit, quota.used, quota.reserved, quota.remaining) == (3, 0, 0, 3)

    reservation = service.reserve_resource(
        account_id, project_id, "projects", 2, "reserve-1",
        datetime.utcnow() + timedelta(minutes=5),
    )
    assert reservation.status == "active"
    assert service.get_quota(account_id, project_id, "projects").remaining == 1

    result = service.record_consumption(
        account_id, project_id, "projects", 2, reservation.reservation_id,
        "event-1", "consume-1",
    )
    assert result.remaining == 1
    assert service.get_quota(account_id, project_id, "projects").used == 2


def test_idempotent_consumption_replays_original_result(service, project):
    account_id, project_id = project
    first = service.record_consumption(
        account_id, project_id, "projects", 1, None, "event-1", "same-key"
    )
    retry = service.record_consumption(
        account_id, project_id, "projects", 1, None, "event-1", "same-key"
    )
    assert retry.already_committed is True
    assert retry.consumption_id == first.consumption_id
    assert retry.remaining == first.remaining
    assert service.get_quota(account_id, project_id, "projects").used == 1


def test_duplicate_key_with_different_payload_is_rejected(service, project):
    account_id, project_id = project
    service.record_consumption(
        account_id, project_id, "projects", 1, None, "event-1", "same-key"
    )
    with pytest.raises(ValueError, match="IDEMPOTENCY_CONFLICT"):
        service.record_consumption(
            account_id, project_id, "projects", 2, None, "event-1", "same-key"
        )


def test_quota_exceeded(service, project):
    account_id, project_id = project
    with pytest.raises(ValueError, match="QUOTA_EXCEEDED"):
        service.record_consumption(
            account_id, project_id, "projects", 4, None, "event-1", "too-much"
        )


def test_reservations_are_commitments_and_leave_only_unreserved_headroom(service, project):
    account_id, project_id = project
    service.set_subscription_for_test(
        account_id, ProductType.TITAN_FRAMEWORK, PlanName.PLUS,
        SubscriptionStatus.ACTIVE,
    )
    service.record_consumption(
        account_id, project_id, "projects", 4, None, "used-1", "used-key"
    )
    service.reserve_resource(
        account_id, project_id, "projects", 3, "reserve-1",
        datetime.utcnow() + timedelta(minutes=5),
    )
    service.record_consumption(
        account_id, project_id, "projects", 3, None, "headroom-1", "headroom-key"
    )
    with pytest.raises(ValueError, match="QUOTA_EXCEEDED"):
        service.record_consumption(
            account_id, project_id, "projects", 1, None, "headroom-2", "headroom-key-2"
        )


def test_reservation_expiry(service, project):
    account_id, project_id = project
    reservation = service.reserve_resource(
        account_id, project_id, "projects", 1, "expired-reserve",
        datetime.utcnow() - timedelta(seconds=1),
    )
    with pytest.raises(ValueError, match="RESERVATION_EXPIRED"):
        service.record_consumption(
            account_id, project_id, "projects", 1, reservation.reservation_id,
            "event-1", "expired-consume",
        )


def test_consumption_cannot_exceed_reservation(service, project):
    account_id, project_id = project
    reservation = service.reserve_resource(
        account_id, project_id, "projects", 1, "small-reserve",
        datetime.utcnow() + timedelta(minutes=5),
    )
    with pytest.raises(ValueError, match="CONSUMPTION_EXCEEDS_RESERVATION"):
        service.record_consumption(
            account_id, project_id, "projects", 2, reservation.reservation_id,
            "event-1", "too-large",
        )


def test_reservation_cannot_be_consumed_by_another_project(service, project):
    account_id, project_id = project
    other_project = service.register_project(
        account_id, ProductType.TITAN_FRAMEWORK, "OtherProject"
    )
    reservation = service.reserve_resource(
        account_id, project_id, "projects", 1, "scoped-reserve",
        datetime.utcnow() + timedelta(minutes=5),
    )
    with pytest.raises(ValueError, match="RESERVATION_NOT_FOUND"):
        service.record_consumption(
            account_id, other_project.project_id, "projects", 1,
            reservation.reservation_id, "event-1", "scoped-consume",
        )


def test_concurrent_reservations_respect_the_quota(service, project):
    account_id, project_id = project

    def reserve(index: int):
        try:
            return service.reserve_resource(
                account_id, project_id, "projects", 1, f"concurrent-reserve-{index}",
                datetime.utcnow() + timedelta(minutes=5),
            )
        except ValueError as exc:
            return str(exc)

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(reserve, range(8)))
    assert sum(not isinstance(result, str) for result in results) == 3
    assert results.count("QUOTA_EXCEEDED") == 5
    assert service.get_quota(account_id, project_id, "projects").reserved == 3


def test_concurrent_same_consumption_is_committed_once(service, project):
    account_id, project_id = project

    def consume():
        return service.record_consumption(
            account_id, project_id, "projects", 1, None, "event-concurrent",
            "concurrent-key",
        )

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: consume(), range(8)))
    assert {result.consumption_id for result in results}.__len__() == 1
    assert sum(result.already_committed for result in results) == 7
    assert service.get_quota(account_id, project_id, "projects").used == 1


def test_ownership_isolation(service, project):
    _, project_id = project
    with pytest.raises(PermissionError, match="PROJECT_OWNERSHIP_REQUIRED"):
        service.get_quota(999, project_id, "projects")


def test_unknown_entitlement_is_rejected(service, project):
    account_id, project_id = project
    with pytest.raises(ValueError):
        service.check_entitlement(account_id, project_id, "not_real")


def test_expired_subscription_resolves_to_starter(service, project):
    account_id, project_id = project
    service.set_subscription_for_test(
        account_id, ProductType.TITAN_FRAMEWORK, PlanName.PLUS,
        SubscriptionStatus.EXPIRED,
    )
    assert service.get_quota(account_id, project_id, "projects").limit == 3


def test_resolution_is_source_of_truth_not_stale_cache(service, project):
    account_id, project_id = project
    assert service.get_quota(account_id, project_id, "projects").limit == 3
    service.set_subscription_for_test(
        account_id, ProductType.TITAN_FRAMEWORK, PlanName.PLUS,
        SubscriptionStatus.ACTIVE,
    )
    assert service.get_quota(account_id, project_id, "projects").limit == 10