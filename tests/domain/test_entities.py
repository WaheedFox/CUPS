"""Tests for CUPS domain entities (Account, Project, Subscription)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

import pytest

from cups.domain.account import Account
from cups.domain.project import ProductType
from cups.domain.subscription import PlanName, Subscription, SubscriptionStatus


class TestAccount:
    def test_creation_with_required_fields(self):
        acc = Account(account_id=12345)
        assert acc.account_id == 12345
        assert acc.status == "active"
        assert acc.username is None
        assert isinstance(acc.created_at, datetime)

    def test_creation_with_username(self):
        acc = Account(account_id=99, username="waheed")
        assert acc.username == "waheed"

    def test_account_id_is_telegram_user_id(self):
        # account_id is an integer — no UUIDs, no strings
        acc = Account(account_id=987654321)
        assert isinstance(acc.account_id, int)


class TestProductType:
    def test_all_four_product_types_exist(self):
        assert ProductType.TITAN_FRAMEWORK.value == "titan-framework"
        assert ProductType.BOT.value == "bot"
        assert ProductType.MINI_APP.value == "mini-app"
        assert ProductType.GAME.value == "game"

    def test_product_type_from_string(self):
        pt = ProductType("titan-framework")
        assert pt == ProductType.TITAN_FRAMEWORK


class TestProject:
    def test_creation(self):
        from cups.domain.project import Project
        pid = uuid4()
        p = Project(
            project_id=pid,
            owner_id=123,
            product=ProductType.TITAN_FRAMEWORK,
            name="MyBot",
        )
        assert p.project_id == pid
        assert p.owner_id == 123
        assert p.product == ProductType.TITAN_FRAMEWORK
        assert p.name == "MyBot"
        assert p.status == "active"

    def test_project_id_is_full_uuid(self):
        from cups.domain.project import Project
        pid = uuid4()
        p = Project(project_id=pid, owner_id=1, product=ProductType.BOT, name="X")
        # Must be a full UUID — not truncated
        assert isinstance(p.project_id, UUID)
        assert len(str(p.project_id)) == 36  # standard UUID string length


class TestSubscription:
    def test_creation(self):
        sub = Subscription(
            subscription_id=str(uuid4()),
            account_id=123,
            product="titan-framework",
            plan=PlanName.STARTER,
            status=SubscriptionStatus.ACTIVE,
        )
        assert sub.plan == PlanName.STARTER
        assert sub.status == SubscriptionStatus.ACTIVE
        assert sub.period == "monthly"

    def test_all_statuses_exist(self):
        statuses = {s.value for s in SubscriptionStatus}
        assert statuses == {"trial", "active", "grace", "frozen", "expired"}

    def test_all_plans_exist(self):
        plans = {p.value for p in PlanName}
        assert plans == {"starter", "plus", "core", "ultra"}
