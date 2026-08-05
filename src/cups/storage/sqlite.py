"""SQLite-backed storage for CUPS Phase 1.

Uses Python's built-in sqlite3 — no external dependencies.

Connection strategy:
  A single persistent connection per SQLiteStore instance is shared across all
  repositories. This is required for :memory: databases (each new connection to
  :memory: creates a separate, empty database). It also works correctly for
  file-based databases in single-process deployments (Phase 1).

Thread safety: check_same_thread=False is set. The CUPS API and bot are
single-threaded workers; this is acceptable for Phase 1.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from uuid import UUID

from ..domain.account import Account
from ..domain.project import Project, ProductType
from ..domain.subscription import PlanName, Subscription, SubscriptionStatus
from .base import AccountRepository, ProjectRepository, SubscriptionRepository

# ─── Schema ──────────────────────────────────────────────────────────────────

_SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    account_id  INTEGER PRIMARY KEY,
    username    TEXT,
    created_at  TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS projects (
    project_id    TEXT PRIMARY KEY,
    owner_id      INTEGER NOT NULL,
    product       TEXT NOT NULL,
    name          TEXT NOT NULL,
    registered_at TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'active',
    FOREIGN KEY (owner_id) REFERENCES accounts(account_id)
);

CREATE TABLE IF NOT EXISTS subscriptions (
    subscription_id TEXT PRIMARY KEY,
    account_id      INTEGER NOT NULL,
    product         TEXT NOT NULL,
    plan            TEXT NOT NULL,
    status          TEXT NOT NULL,
    period          TEXT NOT NULL DEFAULT 'monthly',
    started_at      TEXT NOT NULL,
    expires_at      TEXT,
    trial_ends_at   TEXT,
    FOREIGN KEY (account_id) REFERENCES accounts(account_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_sub_account_product
    ON subscriptions (account_id, product);
"""

# ─── Helpers ─────────────────────────────────────────────────────────────────

def _parse_dt(val: str | None) -> datetime | None:
    return datetime.fromisoformat(val) if val else None


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


# ─── Store ────────────────────────────────────────────────────────────────────

class SQLiteStore:
    """Holds a single SQLite connection shared across all repositories.

    This is required so that :memory: databases work correctly in tests — each
    new sqlite3.connect(':memory:') would create a separate empty database.
    """

    def __init__(self, db_path: str | Path = "cups.db") -> None:
        self._conn = sqlite3.connect(
            str(db_path), check_same_thread=False
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    @property
    def accounts(self) -> "SQLiteAccountRepo":
        return SQLiteAccountRepo(self._conn)

    @property
    def projects(self) -> "SQLiteProjectRepo":
        return SQLiteProjectRepo(self._conn)

    @property
    def subscriptions(self) -> "SQLiteSubscriptionRepo":
        return SQLiteSubscriptionRepo(self._conn)

    def close(self) -> None:
        self._conn.close()


# ─── Account Repository ───────────────────────────────────────────────────────

class SQLiteAccountRepo(AccountRepository):
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def get(self, account_id: int) -> Account | None:
        row = self._conn.execute(
            "SELECT * FROM accounts WHERE account_id = ?", (account_id,)
        ).fetchone()
        if row is None:
            return None
        return Account(
            account_id=row["account_id"],
            username=row["username"],
            created_at=datetime.fromisoformat(row["created_at"]),
            status=row["status"],
        )

    def create(self, account: Account) -> None:
        self._conn.execute(
            "INSERT INTO accounts (account_id, username, created_at, status) "
            "VALUES (?, ?, ?, ?)",
            (account.account_id, account.username,
             account.created_at.isoformat(), account.status),
        )
        self._conn.commit()


# ─── Project Repository ───────────────────────────────────────────────────────

class SQLiteProjectRepo(ProjectRepository):
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def get(self, project_id: UUID) -> Project | None:
        row = self._conn.execute(
            "SELECT * FROM projects WHERE project_id = ?", (str(project_id),)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_project(row)

    def get_by_owner(self, owner_id: int) -> list[Project]:
        rows = self._conn.execute(
            "SELECT * FROM projects WHERE owner_id = ? ORDER BY registered_at",
            (owner_id,),
        ).fetchall()
        return [self._row_to_project(row) for row in rows]

    def create(self, project: Project) -> None:
        self._conn.execute(
            "INSERT INTO projects "
            "(project_id, owner_id, product, name, registered_at, status) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (str(project.project_id), project.owner_id, project.product.value,
             project.name, project.registered_at.isoformat(), project.status),
        )
        self._conn.commit()

    @staticmethod
    def _row_to_project(row: sqlite3.Row) -> Project:
        return Project(
            project_id=UUID(row["project_id"]),
            owner_id=row["owner_id"],
            product=ProductType(row["product"]),
            name=row["name"],
            registered_at=datetime.fromisoformat(row["registered_at"]),
            status=row["status"],
        )


# ─── Subscription Repository ──────────────────────────────────────────────────

class SQLiteSubscriptionRepo(SubscriptionRepository):
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def get(self, account_id: int, product: str) -> Subscription | None:
        row = self._conn.execute(
            "SELECT * FROM subscriptions WHERE account_id = ? AND product = ?",
            (account_id, product),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_sub(row)

    def create(self, subscription: Subscription) -> None:
        self._conn.execute(
            "INSERT INTO subscriptions "
            "(subscription_id, account_id, product, plan, status, period, "
            "started_at, expires_at, trial_ends_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (subscription.subscription_id, subscription.account_id,
             subscription.product, subscription.plan.value,
             subscription.status.value, subscription.period,
             subscription.started_at.isoformat(),
             _iso(subscription.expires_at), _iso(subscription.trial_ends_at)),
        )
        self._conn.commit()

    def update(self, subscription: Subscription) -> None:
        self._conn.execute(
            "UPDATE subscriptions SET plan = ?, status = ?, period = ?, "
            "expires_at = ?, trial_ends_at = ? "
            "WHERE subscription_id = ?",
            (subscription.plan.value, subscription.status.value, subscription.period,
             _iso(subscription.expires_at), _iso(subscription.trial_ends_at),
             subscription.subscription_id),
        )
        self._conn.commit()

    @staticmethod
    def _row_to_sub(row: sqlite3.Row) -> Subscription:
        return Subscription(
            subscription_id=row["subscription_id"],
            account_id=row["account_id"],
            product=row["product"],
            plan=PlanName(row["plan"]),
            status=SubscriptionStatus(row["status"]),
            period=row["period"],
            started_at=datetime.fromisoformat(row["started_at"]),
            expires_at=_parse_dt(row["expires_at"]),
            trial_ends_at=_parse_dt(row["trial_ends_at"]),
        )
